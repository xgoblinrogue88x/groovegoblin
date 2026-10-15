import os
import tkinter as tk
import unittest
from unittest.mock import patch
import test_lite


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class PortraitTests(unittest.TestCase):
    setUp=test_lite.LiteTests.setUp
    tearDown=test_lite.LiteTests.tearDown
    load=test_lite.LiteTests.load
    wait=test_lite.LiteTests.wait

    def phone(self,width=412,height=850):
        a=self.app;a.maxsize(4096,4096)
        if not hasattr(self,'errors'):
            self.errors=[];a.report_callback_exception=lambda kind,value,trace:self.errors.append(str(value))
        a.geometry(f'{width}x{height}');a.update();a._responsive.apply();a.update()
        return a

    def inside(self,widget):
        a=self.app
        self.assertTrue(widget.winfo_ismapped(),str(widget))
        self.assertGreaterEqual(widget.winfo_rootx(),a.winfo_rootx())
        self.assertGreaterEqual(widget.winfo_rooty(),a.winfo_rooty())
        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),a.winfo_rootx()+a.winfo_width())
        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),a.winfo_rooty()+a.winfo_height())

    def test_portrait_and_desktop_repeated_resizes_keep_actions_and_active_pane_inside(self):
        for width,height in ((360,540),(412,915),(540,1170),(1080,2340),(1440,3120),(1088,550),(412,850),(1920,1080)):
            a=self.phone(width,height);portrait=height>width*1.15 or width<800
            self.assertEqual(a._phone.active,portrait)
            for b in a.lite_buttons:self.inside(b)
            if portrait:
                self.inside(a._phone.nav)
                for name in ('Albums','Match','Results','Options','Albums'):
                    a._phone.select(name);a.update()
                    for b in a._phone.strip_buttons:self.inside(b)
                    expected=a._responsive.w['center'] if name=='Albums' else (a._phone.options_host if name=='Options' else a._phone.right)
                    self.inside(expected)
                self.assertGreaterEqual(a.lite_buttons[0].winfo_height(),44)
            else:
                self.assertFalse(a._phone.header.winfo_ismapped())
                self.assertTrue(a._responsive.w['sidebar'].winfo_ismapped())
                self.assertEqual(len({b.winfo_rooty() for b in a.lite_buttons}),1)
                self.assertTrue(a.lite_formats.winfo_ismapped())
        self.assertEqual(self.errors,[])

    def test_editor_form_scrolls_to_save_and_lookup_buttons_fit(self):
        a=self.phone(360,640);e=a.track_editor
        a.tabs.select(e);a.update();a._responsive.apply();a.update()
        for b in e.top_buttons:self.inside(b)
        for b in a._phone.track_tabs:self.inside(b)
        a._phone.select_tracks('Tags & Artwork');a.update();a._phone.tags_host.fit()
        a._phone.tags_host.canvas.yview_moveto(1);a.update()
        for b in (e.save_button,e.undo_button):self.inside(b)
        a._phone.select_tracks('Tracks');a.update();self.inside(e.tree)
        for b in (e.clear_list_button,e.clear_selected_button,a._phone.select_tracks_button):self.inside(b)
        a.tabs.select(a.lookup_page);a.update();a._responsive.apply();a.update()
        for b in (a.lookup_page.search_button,a.lookup_page.cancel_button,a.lookup_page.choose_button,a.lookup_page.scan_button):self.inside(b)
        self.assertEqual(self.errors,[])

    def test_options_and_touch_multi_selection_change_no_music(self):
        a=self.phone();paths=self.load();a.update();before={p:p.read_bytes() for p in paths}
        a._phone.select('Options');a.update()
        for combo,var in a._phone.rename_controls:
            var.set(False)
        a._phone.options_changed();a.refresh_preview()
        self.assertFalse(a.opt_filenames.get());self.assertFalse(a.opt_folders.get())
        self.assertTrue(all(str(c.cget('state'))=='disabled' for c,_ in a._phone.rename_controls))
        self.assertTrue(all(p['folder']==p['dest_folder'] for p in a.actions))
        a._phone.select('Albums');a.update();a._phone.toggle_multi()
        body=a.albums_tree.body
        body.event_generate('<Button-1>',x=65,y=30);body.event_generate('<Button-1>',x=65,y=130);a.update()
        self.assertEqual(len(a.albums_tree.selection()),2)
        with patch('tkinter.messagebox.askyesno',return_value=True):a.remove_albums_button.invoke()
        self.assertFalse(a.matched);self.assertEqual(before,{p:p.read_bytes() for p in paths})
        self.assertEqual(self.errors,[])

    def test_phone_about_settings_and_verify_dialog_fit(self):
        a=self.phone(360,640);self.load()
        a.show_about();a.update();self.inside(a._about_window);a._about_window.destroy()
        a.verify_all();a.update();self.inside(a.verify_dialog);a.verify_dialog.destroy()
        a.show_settings();a.update()
        windows=[c for c in a.winfo_children() if isinstance(c,tk.Toplevel)]
        self.assertEqual(len(windows),1);self.inside(windows[0]);windows[0].destroy()
        self.assertEqual(self.errors,[])

    def test_phone_launch_mode_is_available_on_landscape_remote_desktops(self):
        a=self.phone(1088,550);self.assertFalse(a._phone.active)
        a._phone.open_phone();a.update();a._responsive.apply();a.update()
        self.assertTrue(a._phone.active);self.assertEqual(a._phone.mode.get(),'Phone')
        self.assertLess(a.winfo_width(),a.winfo_height())
        a.geometry('1088x550');a.update();a._responsive.apply();a.update();self.assertTrue(a._phone.active)
        a._phone.mode.set('Auto');a._responsive.apply();a.update();self.assertFalse(a._phone.active)
        self.assertEqual(self.errors,[])

    def test_styled_navigation_popup_keeps_choices_and_changes_section(self):
        a=self.phone(360,640);nav=a._phone.nav
        self.assertEqual(tuple(nav.cget('values')),tuple(b.text for b in a.nav_buttons.values()))
        self.assertEqual(nav.cget('style'),'Mobile.Nav.TCombobox')
        a._phone.style_nav_popup()
        popup=str(nav.tk.call('ttk::combobox::PopdownWindow',str(nav)))
        self.assertEqual(nav.tk.call(popup+'.f.l','cget','-background'),'#101c23')
        self.assertEqual(nav.tk.call(popup+'.f.l','cget','-selectforeground'),'#c0ffda')
        nav.tk.call('ttk::combobox::Post',str(nav));a.update()
        self.assertTrue(int(nav.tk.call('winfo','ismapped',popup)))
        self.assertEqual(int(nav.tk.call(popup+'.f.l','size')),len(a.nav_buttons))
        nav.tk.call('ttk::combobox::Unpost',str(nav))
        nav.current(2);nav.event_generate('<<ComboboxSelected>>');a.update()
        self.assertEqual(a._active_page,'tracks')
        self.assertEqual(self.errors,[])
