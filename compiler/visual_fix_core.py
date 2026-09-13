#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rep(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise RuntimeError(f"bad anchor {path}: {old!r} count={s.count(old)}")
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")

# VM: presentation reason is part of the internal VM/frontend contract.
rep("c48/vm.py", "                 display_present:Callable[[],None]|None=None,\n",
    "                 display_present:Callable[[str],None]|None=None,\n")
rep("c48/vm.py", "        self.display_present=display_present or (lambda:None)\n",
    "        self.display_present=display_present or (lambda _reason:None)\n")
rep("c48/vm.py",
    "    def _b_yield(self,a):\n        self.display_update();self.display_present();return Value(INT,0)\n",
    "    def _b_yield(self,a):\n        self.display_update();self.display_present(\"yield\")\n        return Value(INT,0)\n")
rep("c48/vm.py",
    "        self.display_update();self.display_present();time.sleep(ticks/50.0)\n",
    "        self.display_update();self.display_present(\"sleep\")\n        time.sleep(ticks/50.0)\n")
rep("c48/vm.py",
    "        self.display_update();self.display_present()\n        return Value(INT,self.input_provider())\n",
    "        self.display_update();self.display_present(\"input\")\n        return Value(INT,self.input_provider())\n")
rep("c48/vm.py",
    "        # Publish and paint the logical frame before the 50-Hz delay.  This\n        # keeps animation sleeps from hiding a frame behind the next scene.\n",
    "        # Publish and visibly release the frame before the 50-Hz host delay.\n        # GUI backpressure may slow execution; it never authorizes frame drops.\n")

# GUI: separate Tk commit from visual release.
rep("c48/gui.py", "FRAME_HEIGHT = HEIGHT + BORDER_Y * 2\n\n",
    "FRAME_HEIGHT = HEIGHT + BORDER_Y * 2\n# Tk has no portable compositor-present fence. Animation barriers wait for\n# idle drawing plus a conservative host-visible dwell before VM progression.\nVISUAL_FRAME_DWELL_MS = 80\n\n")
rep("c48/gui.py",
    "        self._frame_border = int(self.screen.border_color) & 7\n        self._rendered_generation = -1\n",
    "        self._frame_border = int(self.screen.border_color) & 7\n        self._committed_generation = -1\n        self._presented_generation = -1\n        self._present_target = -1\n        self._present_reason: str | None = None\n        self._present_scheduled_generation = -1\n")
old = '''    def present(self) -> None:
        """Wait until Tk has painted the latest intentionally published frame."""
        with self._frame_cond:
            target = self._frame_generation
            while self._rendered_generation < target and not self._stop:
                self._frame_cond.wait()

    def _frame_after(
        self,
        rendered_generation: int,
    ) -> tuple[int, bytes, int] | None:
        with self._frame_lock:
            if self._frame_generation == rendered_generation:
                return None
            return (
                self._frame_generation,
                self._frame_snapshot,
                self._frame_border,
            )

    def _mark_rendered(self, generation: int) -> None:
        with self._frame_cond:
            if generation > self._rendered_generation:
                self._rendered_generation = generation
            self._frame_cond.notify_all()
'''
new = '''    def present(self, reason: str = "yield") -> None:
        """Wait for the latest intentional frame to reach its release fence."""
        if reason not in {"yield", "sleep", "input"}:
            raise ValueError(f"invalid presentation reason: {reason}")
        with self._frame_cond:
            target = self._frame_generation
            if target <= self._presented_generation:
                return
            self._present_target = target
            self._present_reason = reason
            self._frame_cond.notify_all()
            while self._presented_generation < target and not self._stop:
                self._frame_cond.wait()

    def _frame_after(
        self,
        committed_generation: int,
    ) -> tuple[int, bytes, int] | None:
        with self._frame_lock:
            if self._frame_generation == committed_generation:
                return None
            return (
                self._frame_generation,
                self._frame_snapshot,
                self._frame_border,
            )

    def _mark_committed(self, generation: int) -> None:
        with self._frame_cond:
            if generation > self._committed_generation:
                self._committed_generation = generation
            self._frame_cond.notify_all()

    def _take_present_request(self) -> tuple[int, str] | None:
        with self._frame_cond:
            target = self._present_target
            if (
                target <= self._presented_generation
                or target > self._committed_generation
                or target <= self._present_scheduled_generation
            ):
                return None
            reason = self._present_reason or "yield"
            self._present_scheduled_generation = target
            return target, reason

    def _mark_presented(
        self, generation: int, reason: str, dwell_ms: int
    ) -> None:
        self._probe(
            "frame_presented",
            generation=int(generation),
            reason=reason,
            dwell_ms=int(dwell_ms),
        )
        with self._frame_cond:
            if generation > self._presented_generation:
                self._presented_generation = generation
            self._frame_cond.notify_all()
'''
rep("c48/gui.py", old, new)
rep("c48/gui.py", "        threading.Thread(target=worker, daemon=True).start()\n\n        def redraw():\n",
    '''        threading.Thread(target=worker, daemon=True).start()

        image_id = None

        def release_presented(generation: int, reason: str, dwell_ms: int) -> None:
            self._mark_presented(generation, reason, dwell_ms)

        def schedule_ready_presentation() -> None:
            request = self._take_present_request()
            if request is None:
                return
            generation, reason = request
            if reason == "input":
                root.after_idle(release_presented, generation, reason, 0)
            else:
                root.after(
                    VISUAL_FRAME_DWELL_MS,
                    release_presented,
                    generation,
                    reason,
                    VISUAL_FRAME_DWELL_MS,
                )

        def redraw():
            nonlocal image_id
''')
rep("c48/gui.py", "            frame = self._frame_after(self._rendered_generation)\n",
    "            frame = self._frame_after(self._committed_generation)\n")
rep("c48/gui.py",
    "                canvas.delete(\"all\")\n                canvas.create_image(0, 0, image=photo, anchor=\"nw\")\n                if self._probe_path:\n                    root.update_idletasks()\n",
    '''                if image_id is None:
                    image_id = canvas.create_image(
                        0, 0, image=photo, anchor="nw"
                    )
                else:
                    canvas.itemconfigure(image_id, image=photo)
                # Flush deferred Tk drawing but never run a nested full loop.
                root.update_idletasks()
                if self._probe_path:
''')
rep("c48/gui.py", '                        f"{probe_path.stem}-frame.ppm"\n',
    '                        f"{probe_path.stem}-frame-{generation}.ppm"\n')
rep("c48/gui.py",
    "                self._mark_rendered(generation)\n            if result[\"done\"]:\n",
    "                self._mark_committed(generation)\n            schedule_ready_presentation()\n            if result[\"done\"]:\n")

# Unit/regression tests: commit is not enough; release reason is observable.
rep("tests/test_gui_framebuffer.py", "    TkDisplay,\n",
    "    TkDisplay,\n    VISUAL_FRAME_DWELL_MS,\n")
old = '''    def test_present_waits_for_the_published_generation(self):
        display = TkDisplay(new_screen())
        generation = display.update()
        finished = []
        thread = threading.Thread(
            target=lambda: (display.present(), finished.append(True))
        )
        thread.start()
        time.sleep(0.02)
        self.assertTrue(thread.is_alive())
        self.assertEqual(finished, [])
        display._mark_rendered(generation)
        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(finished, [True])

        closing = TkDisplay(new_screen())
        closing.update()
        released = []
        waiter = threading.Thread(
            target=lambda: (closing.present(), released.append(True))
        )
        waiter.start()
        time.sleep(0.02)
        self.assertTrue(waiter.is_alive())
        closing.close()
        waiter.join(1.0)
        self.assertFalse(waiter.is_alive())
        self.assertEqual(released, [True])
'''
new = '''    def test_present_waits_for_visual_release_not_tk_commit(self):
        display = TkDisplay(new_screen())
        generation = display.update()
        finished = []
        thread = threading.Thread(
            target=lambda: (display.present("yield"), finished.append(True))
        )
        thread.start()
        time.sleep(0.02)
        self.assertTrue(thread.is_alive())
        display._mark_committed(generation)
        time.sleep(0.02)
        self.assertTrue(thread.is_alive())
        self.assertEqual(display._take_present_request(), (generation, "yield"))
        display._mark_presented(generation, "yield", VISUAL_FRAME_DWELL_MS)
        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(finished, [True])

        prompt = TkDisplay(new_screen())
        prompt_generation = prompt.update()
        prompt_done = []
        prompt_thread = threading.Thread(
            target=lambda: (prompt.present("input"), prompt_done.append(True))
        )
        prompt_thread.start()
        time.sleep(0.02)
        prompt._mark_committed(prompt_generation)
        self.assertEqual(
            prompt._take_present_request(), (prompt_generation, "input")
        )
        prompt._mark_presented(prompt_generation, "input", 0)
        prompt_thread.join(1.0)
        self.assertEqual(prompt_done, [True])

        closing = TkDisplay(new_screen())
        closing.update()
        released = []
        waiter = threading.Thread(
            target=lambda: (closing.present("sleep"), released.append(True))
        )
        waiter.start()
        time.sleep(0.02)
        self.assertTrue(waiter.is_alive())
        closing.close()
        waiter.join(1.0)
        self.assertFalse(waiter.is_alive())
        self.assertEqual(released, [True])
'''
rep("tests/test_gui_framebuffer.py", old, new)
rep("tests/test_release_regressions.py",
    '            display_present=lambda: events.append("present"),\n',
    '            display_present=lambda reason: events.append(f"present:{reason}"),\n')
rep("tests/test_release_regressions.py",
    '                "update", "present",\n                "update", "present",\n                "update", "present", "input",\n',
    '                "update", "present:yield",\n                "update", "present:sleep",\n                "update", "present:input", "input",\n')
