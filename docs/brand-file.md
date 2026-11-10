# The brand file

`patchwork rebrand` takes one JSON file. Add `"$schema"` to get autocompletion and validation in VS Code and Cursor.

```json
{
  "$schema": "https://raw.githubusercontent.com/Abdeltoto/patchwork/main/brand.schema.json",
  "name": "Maple & Oak",
  "colors": {
    "0091CE": "2F5D50",
    "F2F2F2": "F7F3EC"
  },
  "fonts": {
    "HelveticaNeue,HelveticaNeue": "Georgia,Georgia",
    "HelveticaNeue-Bold,HelveticaNeue-Bold": "Georgia,Georgia-Bold"
  },
  "logo": {
    "image": "logo.png",
    "width": 464,
    "replace": "Admin::Logo Global",
    "field": "Brand Logo"
  }
}
```

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | Brand name. The rewritten theme is renamed to it, and the run checks that the rename really happened. |
| `theme` | no | Theme to rewrite, by display or internal name. Default: the theme used by most layouts. |
| `colors` | no | Old hex color to new hex color. Applied to the theme and to every layout's local styles. Alpha is kept. |
| `fonts` | no | Old font to new font, each as `WindowsName,MacPostScriptName`. |
| `logo.image` | with `logo` | PNG, relative to the brand file. Use a transparent PNG. |
| `logo.replace` | with `logo` | The container currently shown as the logo, as `Table::Field`. Every layout object that shows it will show the new logo. |
| `logo.field` | no | Name of the new global field holding the logo. Default `Brand Logo`. |
| `logo.width` | no | Resize the PNG to this width first (needs `pip install "fm-patchwork[image]"`). |

## Finding the colors to replace

List the colors a theme uses, most frequent first:

```bash
patchwork open app.fmp12 --account Admin
patchwork palette
```

```
Apex Blue
FFFFFF  582x
E6E6E6  193x
0091CE  169x
000000  96x
...
```

Map the brand colors you want to change and leave white, black and the greys you want to keep out of the map.

## Finding the logo field

In most Claris starter solutions the header logo is a global container. List the fields of the table that holds the settings and look for a `Container` one:

```bash
patchwork ls fields Admin
```

In the Invoice solution it is `Admin::Logo Global`.

## Fonts

The new font must be installed on every machine that opens the file, or FileMaker falls back to a default font. Fonts that ship with both Windows and macOS (Georgia, Verdana, Arial, Trebuchet MS) are the safe choice.
