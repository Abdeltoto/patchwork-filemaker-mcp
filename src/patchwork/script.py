"""Script steps as FileMaker text, both ways.

`render` turns any <Step> into one line, the way the Script Workspace shows it:
    Set Field [ Clients::Status ; "Gold" ]
`build` turns those lines back into <Step> XML for the steps in STEP_IDS. The XML shapes and
<Options> bits were read from real Save-as-XML exports (FileMaker 20 to 2026).
A line that is exactly the rendering of a step already in the script reuses that step's XML,
so any step, supported or not, survives an edit of the text around it.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

from patchwork import PatchworkError, objects
from patchwork.export import Export, escape, unescape

BLOCK_OPEN = {"If", "Loop"}
BLOCK_MIDDLE = {"Else If", "Else"}
BLOCK_CLOSE = {"End If", "End Loop"}
ON_OFF = {"True": "On", "False": "Off"}


# ---------- reading ----------


def cdata(xml: str) -> str:
    found = re.search(r"<!\[CDATA\[([\s\S]*?)\]\]>", xml)
    return re.sub(r"\r\n|\r", "\n", found.group(1)) if found else ""


def param(step: str, kind: str) -> str:
    found = re.search(
        rf'<Parameter type="{re.escape(kind)}"[^>]*>([\s\S]*?)</Parameter>\s*(?=<Parameter type=|</ParameterValues>)',
        step,
    )
    return found.group(1) if found else ""


def calc(step: str, position: str | None = None) -> str:
    """Calculation text of a step parameter, by its position attribute."""
    pattern = (
        rf'<Calculation datatype="\d+" position="{position}">'
        if position
        else r'<Calculation datatype="\d+" position="\d+">'
    )
    found = re.search(pattern + r"[\s\S]*?</Calculation>\s*</Calculation>", step)
    return cdata(found.group(0)) if found else ""


def field_name(xml: str) -> str:
    ref = re.search(r'<FieldReference [^>]*\bname="([^"]*)"[\s\S]*?</FieldReference>', xml)
    if not ref:
        return ""
    to = re.search(r'<TableOccurrenceReference [^>]*\bname="([^"]*)"', ref.group(0))
    rep = re.search(r"<repetition>[\s\S]*?</repetition>", ref.group(0))
    rep_text = cdata(rep.group(0)) if rep else "1"
    name = f"{unescape(to.group(1))}::{unescape(ref.group(1))}" if to else unescape(ref.group(1))
    return name + (f"[{rep_text}]" if rep_text not in ("", "1") else "")


def booleans(step: str) -> list[tuple[str, str]]:
    return [
        (unescape(t or ""), v)
        for t, v in re.findall(r'<Boolean (?:type="([^"]*)" )?id="\d+" value="(True|False)"', step)
        if t != "Collapsed"
    ]


def quoted(name: str) -> str:
    return '"' + name + '"'


def render(step: str) -> str:
    head = step[: step.index(">")]
    name = unescape(re.search(r'\sname="([^"]*)"', head).group(1))
    off = "// " if 'enable="False"' in head else ""
    if name == "# (comment)":
        comment = re.search(r'<Comment value="([^"]*)"', step)
        text = html.unescape(comment.group(1)) if comment else ""
        return f"{off}# {text}".rstrip().replace("\r", "\n").replace("\n", "¶")
    parts = RENDERERS.get(name, generic)(step)
    if not parts:
        return f"{off}{name}"
    out = f"{off}{name} [ "
    for i, part in enumerate(parts):
        out += part + ("\n" if "//" in part.rsplit("\n", 1)[-1] else " ")
        out += "; " if i < len(parts) - 1 else "]"
    return out


def generic(step: str) -> list[str]:
    parts = []
    field = field_name(step)
    if field:
        parts.append(field)
    for ref in ("ScriptReference", "LayoutReference"):
        found = re.search(rf'<{ref} [^>]*\bname="([^"]*)"', step)
        if found:
            parts.append(quoted(unescape(found.group(1))))
    parts += [f"{t}: {ON_OFF[v]}" if t else ON_OFF[v] for t, v in booleans(step)]
    parts += [unescape(n) for n in re.findall(r'<List name="([^"]*)"', step) if n not in ("From list", "Always")]
    parts += [
        cdata(c)
        for c in re.findall(
            r'<Calculation datatype="\d+" position="(?!10")\d+">[\s\S]*?</Calculation>\s*</Calculation>', step
        )
    ]
    return parts


def render_set_variable(step: str) -> list[str]:
    name = re.search(r'<Name value="([^"]*)"', step)
    rep = re.search(r"<repetition>[\s\S]*?</repetition>", step)
    rep_text = cdata(rep.group(0)) if rep else "1"
    target = unescape(name.group(1)) if name else "$"
    if rep_text not in ("", "1"):
        target += f"[{rep_text}]"
    value = re.search(r"<value>[\s\S]*?</value>", step)
    return [target, f"Value: {cdata(value.group(0)) if value else ''}"]


def render_go_to_layout(step: str) -> list[str]:
    layout = re.search(r'<LayoutReference [^>]*\bname="([^"]*)"', step)
    container = re.search(r'<LayoutReferenceContainer value="(\d+)"', step)
    parts = [
        quoted(unescape(layout.group(1)))
        if layout
        else "original layout"
        if container and container.group(1) == "1"
        else f"Layout: {calc(step) or '?'}"
    ]
    animation = re.search(r'<Animation name="([^"]*)"', step)
    if animation and animation.group(1) != "None":
        parts.append(f"Animation: {animation.group(1)}")
    return parts


def render_perform_script(step: str) -> list[str]:
    script = re.search(r'<ScriptReference [^>]*\bname="([^"]*)"', step)
    parts = [quoted(unescape(script.group(1))) if script else f"By name: {calc(step, '1')}"]
    parameter = calc(param(step, "Parameter"))
    if parameter:
        parts.append(f"Parameter: {parameter}")
    return parts


def render_dialog(step: str) -> list[str]:
    buttons = [unescape(b) for b in re.findall(r'<Parameter type="Button\d" value="([^"]*)"', step)]
    parts = [calc(param(step, "Title")), calc(param(step, "Message"))]
    if buttons and buttons != ["OK"]:
        parts.append("Buttons: " + ", ".join(quoted(b) for b in buttons))
    return parts


def render_exit_script(step: str) -> list[str]:
    result = calc(step)
    return [f"Text Result: {result}"] if result else []


def render_close_window(step: str) -> list[str]:
    return ["Current Window"] if 'type="current"' in step else generic(step)


def render_switch(step: str) -> list[str]:
    return [ON_OFF[v] for _, v in booleans(step)]


def render_loop(step: str) -> list[str]:
    flush = re.search(r'<List name="([^"]*)"', step)
    return [] if not flush or flush.group(1) == "Always" else [f"Flush: {flush.group(1)}"]


RENDERERS: dict[str, Callable[[str], list[str]]] = {
    "Set Field": lambda s: [field_name(s), calc(s, "0")],
    "Set Variable": render_set_variable,
    "If": lambda s: [calc(s)],
    "Else If": lambda s: [calc(s)],
    "Exit Loop If": lambda s: [calc(s)],
    "Else": lambda s: [],
    "Loop": render_loop,
    "Go to Layout": render_go_to_layout,
    "Perform Script": render_perform_script,
    "Show Custom Dialog": render_dialog,
    "Exit Script": render_exit_script,
    "Close Window": render_close_window,
    "Set Error Capture": render_switch,
    "Allow User Abort": render_switch,
}


def steps_of(xml: str) -> list[str]:
    return re.findall(r"<Step\b[\s\S]*?</Step>", xml)


def name_of(step: str) -> str:
    return unescape(re.search(r'\sname="([^"]*)"', step[: step.index(">")]).group(1))


def to_text(steps_xml: str) -> str:
    lines, depth = [], 0
    for step in steps_of(steps_xml):
        name = name_of(step)
        if name in BLOCK_CLOSE or name in BLOCK_MIDDLE:
            depth = max(depth - 1, 0)
        lines.append("    " * depth + render(step))
        if name in BLOCK_OPEN or name in BLOCK_MIDDLE:
            depth += 1
    return "\n".join(lines)


def normalized(steps_xml: str) -> list[str]:
    return [re.sub(r"\s+", " ", render(s)).strip() for s in steps_of(steps_xml)]


# ---------- writing ----------


def split_lines(text: str) -> list[str]:
    """One entry per step: a line, plus following lines while a [ ... ] is still open."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out, start, depth, state, i = [], None, 0, "", 0
    while i < len(text):
        ch = text[i]
        if start is None:
            if ch.isspace():
                i += 1
                continue
            start, depth, state = i, 0, ""
            head = text[i:].lstrip("/ ")
            if head.startswith("#"):
                end = text.find("\n", i)
                end = len(text) if end < 0 else end
                out.append(text[start:end].strip())
                start, i = None, end
                continue
            if text.startswith("//", i):
                i += 2
                continue
        if state == '"':
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = ""
        elif state == "/*":
            if text.startswith("*/", i):
                state, i = "", i + 1
        elif state == "//":
            if ch == "\n":
                state = ""
                continue
        elif ch == '"':
            state = '"'
        elif text.startswith("/*", i):
            state, i = "/*", i + 1
        elif text.startswith("//", i) and depth > 0:
            state, i = "//", i + 1
        elif ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "\n" and depth <= 0:
            out.append(text[start:i].strip())
            start = None
        i += 1
    if start is not None:
        if depth > 0 or state in ('"', "/*"):
            raise PatchworkError(f"Unclosed [, quote or comment in: {text[start : start + 80]}")
        out.append(text[start:].strip())
    return out


def split_params(inside: str) -> list[str]:
    parts, start, depth, state, i = [], 0, 0, "", 0
    while i < len(inside):
        ch = inside[i]
        if state == '"':
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = ""
        elif state == "/*":
            if inside.startswith("*/", i):
                state, i = "", i + 1
        elif state == "//":
            if ch == "\n":
                state = ""
        elif ch == '"':
            state = '"'
        elif inside.startswith("/*", i):
            state, i = "/*", i + 1
        elif inside.startswith("//", i):
            state, i = "//", i + 1
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ";" and depth == 0:
            parts.append(inside[start:i].strip())
            start = i + 1
        i += 1
    rest = inside[start:].strip()
    if rest or parts:
        parts.append(rest)
    return parts


def parse_line(line: str) -> tuple[str, list[str], bool]:
    text = line.strip()
    enabled = not text.startswith("//")
    if not enabled:
        text = text[2:].strip()
    if text.startswith("#"):
        return "# (comment)", [text[1:].strip()], enabled
    match = re.match(r"([^\[]+?)\s*(?:\[([\s\S]*)\])?\s*$", text)
    if not match:
        raise PatchworkError(f"Cannot read this step: {line.strip()[:80]}")
    return match.group(1).strip(), split_params(match.group(2) or ""), enabled


def labelled(params: list[str], label: str) -> str | None:
    for p in params:
        if p.lower().startswith(label.lower() + ":"):
            return p[len(label) + 1 :].strip()
    return None


def calc_xml(text: str, position: int, datatype: int = 1) -> str:
    if "]]>" in text:
        raise PatchworkError("A calculation cannot contain ']]>'.")
    return f'<Calculation datatype="{datatype}" position="{position}"><Calculation><Text><![CDATA[{text}]]></Text></Calculation></Calculation>'


def step_xml(name: str, options: int, params: list[str] = (), enabled: bool = True) -> str:
    inner = (
        (f'<ParameterValues membercount="{len(params)}">' + "".join(params) + "</ParameterValues>") if params else ""
    )
    return (
        f'<Step id="{STEP_IDS[name]}" name="{escape(name)}" enable="{enabled}"><UUID>{objects.new_uuid()}</UUID>'
        f"<OwnerID></OwnerID><Options>{options}</Options>{inner}</Step>"
    )


def boolean(kind: str, ident: int, value: bool) -> str:
    return (
        f'<Parameter type="Boolean"><Boolean type="{escape(kind)}" id="{ident}" value="{value}"></Boolean></Parameter>'
    )


COLLAPSED = boolean("Collapsed", 33554432, False)
# For these flags the Boolean id is also the bit the step sets in <Options>.
WITH_DIALOG, SKIP_VALIDATION, FORCE_COMMIT = 128, 256, 512
FLUSH_JOINS, FLUSH_EXTERNAL = 256, 512


def on(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    if value.strip().lower() not in ("on", "off"):
        raise PatchworkError(f"Expected On or Off, got: {value}")
    return value.strip().lower() == "on"


def target_field(export: Export, text: str) -> str:
    match = re.fullmatch(r"(.+?::.+?)(?:\[(.+)\])?", text.strip())
    if not match:
        raise PatchworkError(f"Expected a field as Occurrence::Field, got: {text}")
    from patchwork.place import field_target

    field_id, name, field_uuid, to_ref = field_target(export, match.group(1))
    rep = calc_xml(match.group(2) or "1", 10)
    return (
        f'<Parameter type="FieldReference"><FieldReference id="{field_id}" name="{escape(name)}" UUID="{field_uuid}">'
        f"<repetition>{rep}</repetition>{to_ref}</FieldReference></Parameter>"
    )


def unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1]
    return text


def build_step(export: Export, name: str, params: list[str], enabled: bool) -> str:
    def need(count: int) -> None:
        if len(params) < count:
            raise PatchworkError(f"{name} needs {count} parameter(s) in [ ... ], got {len(params)}.")

    if name == "# (comment)":
        text = params[0].replace("¶", "\r") if params else ""
        value = f' value="{escape(text).replace(chr(13), "&#13;")}"' if text else ""
        return step_xml(
            name, 4 if text else 0, [f'<Parameter type="Comment"><Comment{value}></Comment></Parameter>'], enabled
        )
    if name == "Set Field":
        need(2)
        return step_xml(
            name,
            16385,
            [target_field(export, params[0]), f'<Parameter type="Calculation">{calc_xml(params[1], 0)}</Parameter>'],
            enabled,
        )
    if name == "Set Variable":
        need(2)
        match = re.fullmatch(r"(\$\$?[^\[\s]+)(?:\[(.+)\])?", params[0].strip())
        if not match:
            raise PatchworkError(f"Set Variable needs a $name or $$name, got: {params[0]}")
        value = labelled(params[1:], "Value")
        value = params[1] if value is None else value
        return step_xml(
            name,
            16388,
            [
                f'<Parameter type="Variable"><value>{calc_xml(value, 1)}</value><Name value="{escape(match.group(1))}"></Name>'
                f"<repetition>{calc_xml(match.group(2) or '1', 2)}</repetition></Parameter>"
            ],
            enabled,
        )
    if name in ("If", "Else If"):
        need(1)
        return step_xml(
            name, 16384, [COLLAPSED, f'<Parameter type="Calculation">{calc_xml(params[0], 0, 7)}</Parameter>'], enabled
        )
    if name == "Exit Loop If":
        need(1)
        return step_xml(
            name, 16384, [f'<Parameter type="Calculation">{calc_xml(params[0], 0, 7)}</Parameter>'], enabled
        )
    if name == "Else":
        return step_xml(name, 0, [COLLAPSED, COLLAPSED], enabled)
    if name == "Loop":
        return step_xml(
            name, 0, [COLLAPSED, '<Parameter type="List"><List name="Always" value="1"></List></Parameter>'], enabled
        )
    if name == "Go to Layout":
        need(1)
        if params[0].strip().lower() == "original layout":
            container = '<LayoutReferenceContainer value="1"><Label>original layout</Label></LayoutReferenceContainer>'
            options = 0
        else:
            layout = objects.find(export, "layout", unquote(params[0]))
            container = (
                f'<LayoutReferenceContainer value="5"><LayoutReference id="{layout.id}" name="{escape(layout.name)}" '
                f'UUID="{layout.uuid}"></LayoutReference></LayoutReferenceContainer>'
            )
            options = 8
        return step_xml(
            name,
            options,
            [
                f'<Parameter type="LayoutReferenceContainer">{container}</Parameter>',
                '<Parameter type="Animation"><Animation name="None" value="0"></Animation></Parameter>',
            ],
            enabled,
        )
    if name == "Perform Script":
        need(1)
        script = objects.find(export, "script", unquote(params[0]))
        parameter = labelled(params[1:], "Parameter")
        inner = calc_xml(parameter, 0) if parameter else ""
        return step_xml(
            name,
            16448 if parameter else 64,
            [
                f'<Parameter type="List"><List name="From list" value="1"><ScriptReference id="{script.id}" name="{escape(script.name)}" '
                f'UUID="{script.uuid}"></ScriptReference></List></Parameter>',
                f'<Parameter type="Parameter"><Parameter>{inner}</Parameter></Parameter>',
            ],
            enabled,
        )
    if name == "Show Custom Dialog":
        need(2)
        buttons = labelled(params[2:], "Buttons")
        labels = re.findall(r'"([^"]*)"', buttons) if buttons else ["OK"]
        if len(labels) > 3:
            raise PatchworkError("Show Custom Dialog has at most 3 buttons.")
        labels += [""] * (3 - len(labels))
        button_xml = "".join(
            f'<Parameter type="Button{i + 1}"{" value=" + chr(34) + escape(b) + chr(34) if b else ""}>'
            f'<Boolean type="Commit" value="{i == 0}"></Boolean></Parameter>'
            for i, b in enumerate(labels)
        )
        return step_xml(
            name,
            16388,
            [
                f'<Parameter type="Title">{calc_xml(params[0], 0)}</Parameter>',
                f'<Parameter type="Message">{calc_xml(params[1], 1)}</Parameter>',
                button_xml,
            ],
            enabled,
        )
    if name == "Exit Script":
        result = labelled(params, "Text Result")
        result = params[0] if result is None and params else result
        if not result:
            return step_xml(name, 0, enabled=enabled)
        return step_xml(name, 16384, [f'<Parameter type="Calculation">{calc_xml(result, 0)}</Parameter>'], enabled)
    if name in ("Commit Records/Requests", "Delete Record/Request"):
        dialog = on(labelled(params, "With dialog"), True)
        options = 0 if dialog else WITH_DIALOG
        values = [boolean("With dialog", WITH_DIALOG, dialog)]
        if name == "Commit Records/Requests":
            skip, force = (
                on(labelled(params, "Skip data entry validation"), False),
                on(labelled(params, "Force Commit"), False),
            )
            options += SKIP_VALIDATION * skip + FORCE_COMMIT * force
            values = [
                boolean("Skip data entry validation", SKIP_VALIDATION, skip),
                *values,
                boolean("Force Commit", FORCE_COMMIT, force),
            ]
        return step_xml(name, options, values, enabled)
    if name in ("Set Error Capture", "Allow User Abort"):
        need(1)
        value = on(params[0], True)
        return step_xml(
            name,
            196608 if value else 65536,
            [f'<Parameter type="Boolean"><Boolean id="131072" value="{value}"></Boolean></Parameter>'],
            enabled,
        )
    if name == "Refresh Window":
        join, external = (
            on(labelled(params, "Flush cached join results"), False),
            on(labelled(params, "Flush cached external data"), False),
        )
        return step_xml(
            name,
            FLUSH_JOINS * join + FLUSH_EXTERNAL * external,
            [
                boolean("Flush cached join results", FLUSH_JOINS, join),
                boolean("Flush cached external data", FLUSH_EXTERNAL, external),
            ],
            enabled,
        )
    if name == "Close Window":
        return step_xml(
            name,
            -2147483648,
            [
                '<Parameter type="WindowReference"><WindowReference><Select kind="0" type="current">'
                "</Select></WindowReference></Parameter>"
            ],
            enabled,
        )
    if name in NO_PARAMS:
        return step_xml(name, 0, enabled=enabled)
    raise PatchworkError(
        f"Unknown step for text: {name}. Text works for: {', '.join(sorted(STEP_IDS))}. "
        f"For another step, keep its line exactly as `show script` prints it, or pass <Step> XML "
        f"(see `patchwork show step {name!r}`)."
    )


NO_PARAMS = {"End If", "End Loop", "Freeze Window", "New Record/Request", "Show All Records", "Halt Script", "Beep"}
STEP_IDS = {
    "# (comment)": 89,
    "Set Field": 76,
    "Set Variable": 141,
    "If": 68,
    "Else If": 125,
    "Else": 69,
    "End If": 70,
    "Loop": 71,
    "Exit Loop If": 72,
    "End Loop": 73,
    "Go to Layout": 6,
    "Perform Script": 1,
    "Show Custom Dialog": 87,
    "Exit Script": 103,
    "Commit Records/Requests": 75,
    "Delete Record/Request": 9,
    "Set Error Capture": 86,
    "Allow User Abort": 85,
    "Refresh Window": 80,
    "Close Window": 121,
    "Freeze Window": 79,
    "New Record/Request": 7,
    "Show All Records": 23,
    "Halt Script": 90,
    "Beep": 93,
}


def build(export: Export, text: str, existing: str = "") -> str:
    """<Step> XML for script text. Lines identical to an existing step reuse that step."""
    known: dict[str, list[str]] = {}
    for step in steps_of(existing):
        known.setdefault(re.sub(r"\s+", " ", render(step)).strip(), []).append(step)
    out = []
    for line in split_lines(text):
        key = re.sub(r"\s+", " ", line).strip()
        if known.get(key):
            out.append(known[key].pop(0))
            continue
        out.append(build_step(export, *parse_line(line)))
    if not out:
        raise PatchworkError("No step found in the text.")
    return "\n".join(out)


def is_xml(steps: str) -> bool:
    return "<Step" in steps
