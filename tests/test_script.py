import unittest

from helpers import FIXTURES, mini_export

from patchwork import PatchworkError, objects, script
from patchwork.export import Export


class ScriptTextTests(unittest.TestCase):
    def setUp(self):
        self.export = mini_export()
        self.fields = Export.load(FIXTURES / "layout-export.xml")

    def round_trip(self, text: str, export=None) -> str:
        return script.to_text(script.build(export or self.export, text))

    def test_reads_an_existing_script(self):
        self.assertEqual(script.to_text(objects.script_steps(self.export, "Close Window")[1]), "# Closes the window")

    def test_blocks_are_indented(self):
        text = "If [ $a ]\n    Beep\nElse If [ $b ]\n    Loop\n        Exit Loop If [ 1 ]\n    End Loop\nElse\n    Halt Script\nEnd If"
        self.assertEqual(self.round_trip(text), text)

    def test_semicolons_inside_calculations_and_comments_are_not_separators(self):
        line = 'Set Variable [ $x ; Value: If ( $a ; "x;y" ; /* a ; b [ */ 2 ) ]'
        self.assertEqual(self.round_trip(line), line)

    def test_a_trailing_line_comment_keeps_the_bracket_outside(self):
        text = self.round_trip("Exit Script [ Text Result: 0 // reset\n]")
        self.assertEqual(text, "Exit Script [ Text Result: 0 // reset\n]")
        self.assertEqual(self.round_trip(text), text)

    def test_set_field_resolves_the_occurrence_and_repetition(self):
        xml = script.build(self.fields, 'Set Field [ Clients::Notes[2] ; "Hi" ]')
        self.assertIn('<FieldReference id="11" name="Notes" UUID="NOTES-UUID">', xml)
        self.assertIn('name="Clients" UUID="TO-UUID"', xml)
        self.assertEqual(script.to_text(xml), 'Set Field [ Clients::Notes[2] ; "Hi" ]')

    def test_dialog_buttons_and_options_bits(self):
        line = 'Show Custom Dialog [ "Title" ; "Sure?" ; Buttons: "Yes, go", "No" ]'
        self.assertEqual(self.round_trip(line), line)
        commit = script.build(
            self.export, "Commit Records/Requests [ Skip data entry validation: On ; With dialog: Off ]"
        )
        self.assertIn("<Options>384</Options>", commit)

    def test_disabled_step_and_multiline_comment(self):
        text = "// Beep\n# first¶second"
        xml = script.build(self.export, text)
        self.assertIn('enable="False"', xml)
        self.assertIn('value="first&#13;second"', xml)
        self.assertEqual(script.to_text(xml), text)

    def test_unknown_step_is_reused_when_unchanged(self):
        existing = (
            '<Step id="999" name="Sort Records" enable="True"><UUID>S</UUID><Options>0</Options>'
            '<ParameterValues membercount="1"><Parameter type="Boolean"><Boolean type="With dialog" id="128" value="False">'
            "</Boolean></Parameter></ParameterValues></Step>"
        )
        line = script.render(existing)
        self.assertEqual(line, "Sort Records [ With dialog: Off ]")
        self.assertIn('id="999"', script.build(self.export, f"Beep\n{line}", existing))
        with self.assertRaisesRegex(PatchworkError, "Unknown step for text: Sort Records"):
            script.build(self.export, line)

    def test_names_that_do_not_exist_are_refused(self):
        with self.assertRaisesRegex(PatchworkError, "layout not found"):
            script.build(self.export, 'Go to Layout [ "Nowhere" ]')
        with self.assertRaisesRegex(PatchworkError, "Unclosed"):
            script.build(self.export, 'If [ "open ]')


if __name__ == "__main__":
    unittest.main()
