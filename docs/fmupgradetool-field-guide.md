# FMUpgradeTool field guide

What the [official guide](https://help.claris.com/en/app-upgrade-tool-guide/content/index.html) does not tell you. Every rule below was verified on real files (FMUpgradeTool 26.0.3.309, FileMaker Pro 26.0.3) by applying a patch, re-exporting the result with `FMDeveloperTool --saveAsXML`, and opening it in FileMaker.

The single most important fact: **FMUpgradeTool prints `Patch File Applied` and exits 0 even when it skipped your change.** `--validatePatch` checks syntax only. The only proof is a re-export of the result. Patchwork does that check after every change (see [section 10](#10-detecting-a-skipped-patch)).

Found something else? [Share it](https://github.com/Abdeltoto/patchwork/issues/new?template=field-guide.yml).

## 1. Run `--generateGUIDs` first

A file that was never patched has objects without a UUID. Themes, for instance, export as `<UUID></UUID>`.

| Without `--generateGUIDs` | Result |
|---|---|
| `Replace type="Theme" UUID=""` | Skipped, success reported |
| `AddAction` on `FieldsForTables` | Skipped, success reported |

Run it once per file, on a copy, and build every patch from an export of that copy. `patchwork open` does both.

## 2. What is applied, what is skipped

| Patch | Applied? |
|---|---|
| `ReplaceAction` > `Replace type="Theme" UUID=…` with the **whole** `<Theme>` | Yes |
| `ReplaceAction` > `Replace type="Layout" UUID=…` with the **whole** `<Layout>` | Yes |
| `ReplaceAction` > `Replace type="ValueList"` / `type="CustomFunction"` with the whole object | Yes |
| `AddAction` > `FieldsForTables` > `FieldCatalog` with one new `<Field>` | Yes, if the rules in section 3 are met |
| `AddAction` > `ValueListCatalog` with a new `<ValueList>` | Yes (section 11) |
| `AddAction` > `CustomFunctionsCatalog` > `ObjectList` with a new `<CustomFunction>` | Yes (section 11) |
| `AddAction` > `ScriptCatalog` + `StepsForScripts` together | Yes, a new script with its steps (section 12) |
| `AddAction` > `StepsForScripts` for an existing script | Yes, steps appended (section 12) |
| `DeleteAction` > `ItemReference type="ScriptReference"` / `"LayoutReference"` / `"ValueListReference"` / `"CustomFunctionReference"` | Yes |
| `DeleteAction` > `ItemReference type="FieldReference"` with a `BaseTableReference` inside | Yes |
| `DeleteAction` > `ItemReference type="ScriptStepReference"` with a `ScriptReference` inside | Yes (section 12) |
| `AddAction` + `ReplaceAction` in the same patch (new field + theme) | Yes |
| `Replace type="LayoutObject"` alone | **Skipped** |
| `ReplaceAction` wrapping a `<LayoutCatalog>` | **Skipped** |
| `AddAction` > `ThemeCatalog` (a brand-new theme) | **Skipped**. Rewrite an existing theme instead, and rename it. |

## 3. Adding a field

An added field is applied only when all of these hold:

- `<FieldsForTables membercount="1">` and `<ObjectList membercount="1">` (the count of what you add, not of the table).
- The `<FieldCatalog>` starts with the catalog `<UUID>`, then a `<TagList></TagList>`, then the `<BaseTableReference … UUID=…>`.
- The field `id` is the highest existing id in that table **plus one**.
- Container fields use `datatype="Binary"`. Timestamps use `datatype="TimeStamp"`.

`patchwork add-field` builds exactly this.

## 4. Finding the right UUID

- **A layout's UUID is the direct child `<UUID>` of `<Layout>`**, near the end of the block, after the parts and the table view. The first `<UUID>` you meet inside a `<Layout>` belongs to a layout object. Using it silently does nothing.
- A theme is matched by its `<UUID>`, its `Display` name is just a label: renaming a theme is a `Display="…"` change inside a whole-theme replace.

## 5. UUIDs change after each patch

FMUpgradeTool gives **new UUIDs** to the fields it adds and to the layout objects inside a replaced layout. It keeps your patch UUID as `SourceUUID`. So:

1. apply patch 1,
2. **re-export**,
3. build patch 2 from the new export.

A patch built from an old export points at UUIDs that no longer exist, and is skipped.

## 6. Layout details that bite

- A field on a layout is a `<FieldReference id="…" name="…" repetition="1" UUID="…">`. The `repetition` attribute must be kept when you swap a field.
- Where an object sits on screen depends on its `<Bounds>` **and** its anchoring, stored as bit flags in the object's `<Options>`. For example `805306368` (`0x30000000`) anchors left and top, `1610612736` (`0x60000000`) anchors top and right, so the object follows the window's right edge. Two objects with correct bounds but different anchoring will drift apart when the window is resized.

## 7. Theme CSS

- Colors are written `rgba(r%,g%,b%,a)` with percentages, for example `rgba(0%,56.8627%,80.7843%,1)` for `#0091CE`.
- Fonts are written `-fm-font-family(WindowsName,MacPostScriptName)`, for example `-fm-font-family(Georgia,Georgia-Bold)`.
- Layouts can override the theme with `<LocalCSS>`: recolor those too, or some objects keep the old brand.

## 8. Embedding an image without touching record data

FMUpgradeTool cannot change record data. To ship a logo inside a patch, add a **global stored calculation** of type container:

```
Base64Decode ( "<base64 of the PNG>" ; "logo.png" )
```

The calculation text is limited to about 30,000 characters, so keep the PNG small (Patchwork refuses anything over 28,000 and can resize with `--image-width`).

## 9. Practical

- The source file must be **closed**. An open file gives error 803.
- FMDeveloperTool refuses to overwrite an existing export unless you pass `-f`.
- The patch `version` attribute should equal the `version` of the FMSaveAsXML it was built from (`2.3.0.0` for FileMaker 2026).
- `--update` and `--generateDBFile` write an `XMLDeserializeResults.log` next to the output, with each catalog processed.

## 10. Detecting a skipped patch

Comparing two exports byte for byte does not work: every save changes the `<FMSaveAsXML …>` header, and FMUpgradeTool touches the attributes of many `<UUID>` elements (`modifications`, `userName`, `accountName`, `timestamp`) even when it skips your change.

Remove the header and those attributes, keep the UUID values, then compare. If the two exports are identical, the patch was skipped. If they differ, compare object by object (kind and name) to see what was added, changed or deleted. Patchwork does exactly this after every change and refuses to record a version that changed nothing.

## 11. Value lists and custom functions

- The two catalogs are not shaped alike. `CustomFunctionsCatalog` wraps its functions in an `<ObjectList membercount="…">`. `ValueListCatalog` holds its `<ValueList>` elements directly.
- A `<ValueList>`'s own `<UUID>` comes **after** `<Source>` and `<CustomValues>`, near the end of the block. A `<CustomFunction>`'s comes first.
- Custom values are one `<Text><![CDATA[…]]>` with one value per line. A carriage return or a line feed both work, and come back as line feeds in the next export. Do **not** write `&#13;` inside the CDATA: it is kept as literal text, and `Gold&#13;Platinum` becomes a single value.
- **A custom function's parameters are an `<ObjectList>` of `<Parameter name="…">` after `<Display>`.** Listing them only in `<Display>` is not enough: FileMaker then rejects the formula, and the function is created **empty**, without any error. Real form:

  ```xml
  <CustomFunction id="11" name="GFN" access="All">
    <UUID>…</UUID>
    <TagList></TagList>
    <Calculation><Text><![CDATA[GetValue ( Substitute ( GetFieldName ( field ) ; "::" ; ¶ ) ; 2 )]]></Text></Calculation>
    <Display>GFN ( field )</Display>
    <ObjectList membercount="1">
      <Parameter name="field"></Parameter>
    </ObjectList>
  </CustomFunction>
  ```

- In general, FileMaker drops a calculation it cannot parse, or a step parameter with an unknown `type`, and still reports success. Check the content after a patch, not only that the object exists. Patchwork re-reads the values of a new value list and the formula and parameters of a new custom function, and drops the version if they are not what was sent.
- As with fields, the new `id` is the highest existing id in the catalog plus one, and the catalog `<UUID>` is copied from the export.

## 12. Scripts and steps

- **A new script with steps** is one `AddAction` with two siblings: the `ScriptCatalog` entry (`<Script id name>` with its `<UUID>` and `<Options>`), then `<StepsForScripts>` holding `<Script><ScriptReference id name UUID/><ObjectList>…steps…</ObjectList></Script>`.
- **Appending steps** to an existing script is the same `StepsForScripts` block alone. Number the new steps from the current count: `index="0"` for the first step of an empty script, `index="8"` after eight steps.
- **Deleting steps** needs one `<ItemReference UUID="step UUID" type="ScriptStepReference">` per step, **each with the script's `<ScriptReference>` inside**. Rewriting a script is that `DeleteAction` followed by an `AddAction` of the new steps, in one patch.
- Every new step needs a fresh `<UUID>`. Drop the `hash` attribute when you copy a step from an export: FileMaker recomputes it.
- Folders and separators in the script and layout catalogs are flat elements with `isFolder="True"` or `isFolder="Marker"`, not containers. Skip them when looking for a script by name.
- Deleting a layout works with `ItemReference type="LayoutReference"`, but scripts that go to that layout are left pointing at nothing. The diff shows them as changed (`~ script …`).
- A step's `<Options>` is a bit field that mirrors its parameters. These values are what FileMaker writes, read from four real exports, and FMUpgradeTool accepts steps written with them:

  | Step | `<Options>` |
  |---|---|
  | `# (comment)` | `4` with text, `0` empty |
  | If, Else If, Exit Loop If, Exit Script with a result | `16384` |
  | Set Field | `16385` |
  | Set Variable, Show Custom Dialog | `16388` |
  | Perform Script | `64`, or `16448` with a parameter |
  | Go to Layout | `8` for a named layout, `0` for original layout |
  | Commit Records/Requests | `+128` without dialog, `+256` skip validation, `+512` force commit |
  | Delete Record/Request | `128` without dialog, `0` with |
  | Set Error Capture, Allow User Abort | `196608` On, `65536` Off |
  | Refresh Window | `+256` flush join results, `+512` flush external data |
  | Close Window (current) | `-2147483648` |

- Step parameters are positional through a `position` attribute on each `<Calculation>`: Set Field's value is `position="0"` and its repetition `position="10"`; Set Variable's value is `1` and its repetition `2`; Show Custom Dialog's title is `0` and message `1`.
- A comment's text is the `value` attribute of `<Comment>`. A line break in it must be written `&#13;`: a raw line break inside an attribute is turned into a space by XML parsers.

## 13. Putting a field on a layout

- `<Bounds>` are absolute: they count from the top of the layout, not from the top of the part. A part's `<Definition>` has its `size` and its `absolute` start.
- A field points at its label through `<Accessibility><Label>ID</Label>`, the label being a `Text` object of the same part.
- Adding an object means replacing the whole layout (section 2). FileMaker renumbers the new objects' ids, and keeps the label link.
- To insert a row: move every object of the part whose top is below the row by its height, grow `Definition size`, move every following part (`absolute` and all its bounds), and stretch background rectangles that cross the row. Patchwork's `place-field` does exactly this, and refuses to place a field over another object.
