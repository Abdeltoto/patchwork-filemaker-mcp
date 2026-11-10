# Examples

Every example uses the free [Invoice Solution](https://marketplace.claris.com/detail/2000.html) from the Claris Marketplace. Its account is `Admin` with no password, hence `--no-password`. Close it in FileMaker first.

## A first session

```bash
patchwork open "Invoice Solution.fmp12" --account Admin --no-password
patchwork ls                       # what is in the file
patchwork ls fields Clients
patchwork show script "Close Window"
```

`open` keeps a working copy in `.patchwork/` next to you. Every command below adds a version you can `undo`.

## Recipes

### Add fields

```bash
patchwork add-field Clients "Loyalty Tier" --comment "Bronze, Silver or Gold"
patchwork add-field Clients "City Line" --calc 'Clients::Main Address City & ", " & Clients::Main Address Country'
patchwork add-field Admin "Watermark" --image watermark.png --image-width 300
```

The last one embeds the image in a global container calculation: no record data is touched.

### Add a value list and a custom function

```bash
patchwork add-value-list "Loyalty Tiers" Bronze Silver Gold
patchwork add-custom-function Greeting --param who --calc '"Hello " & who'
```

### Write a script

Scripts are FileMaker text, one step per line. Save this as `hello.txt`:

```
# Greet the user
Set Variable [ $name ; Value: Get ( AccountName ) ]
If [ IsEmpty ( $name ) ]
    Exit Script [ Text Result: False ]
End If
Show Custom Dialog [ "Hello" ; "Welcome back, " & $name ; Buttons: "OK" ]
```

```bash
patchwork add-script "Say Hello" hello.txt
patchwork show script "Navigation" > nav.txt   # any script, as text
# edit nav.txt
patchwork set-steps "Navigation" nav.txt       # lines you did not touch keep their exact step
```

Each step is re-read after the change: if FileMaker dropped a parameter, the version is refused. For a step that text does not cover yet, `patchwork show step "Sort Records"` prints a real one as XML, and the same commands take `<Step>` XML.

### Put a field on a layout

```bash
patchwork add-field Clients "Loyalty Tier"
patchwork place-field "Clients Details" "Clients::Loyalty Tier" --near "Contact Email" --label "Loyalty tier"
```

The new field copies the look of Contact Email and its label. Everything below moves down and the part grows to make room.

### Edit any object from its XML

```bash
patchwork show value-list "Loyalty Tiers" > vl.xml
# edit vl.xml
patchwork replace value-list "Loyalty Tiers" vl.xml
```

The same works for custom functions and whole layouts. Keep the whole `<Layout>` block: FMUpgradeTool skips a replace of a single layout object.

### Restyle

```bash
patchwork palette
patchwork retheme --colors '{"0091CE": "2F5D50"}' --rename "Forest"
patchwork recolor-layouts --only "Dashboard" "Invoices" --colors colors.json
patchwork recolor-layouts --swap-field "Admin::Logo Global" "Admin::Watermark"
```

### Delete, look back, undo, save

```bash
patchwork delete layout "Dev Line Items"
patchwork log
patchwork undo
patchwork save "Invoice v2.fmp12"
```

## Maple & Oak: rebrand in one command

A fictional brand, to try `rebrand`. It maps the Apex Blue palette to forest green, cream and amber, swaps Helvetica Neue for Georgia, and replaces the Claris logo (`Admin::Logo Global`) on every layout.

```bash
patchwork rebrand "Invoice Solution.fmp12" "Invoice - Maple & Oak.fmp12" \
  --brand examples/maple-and-oak/brand.json --account Admin --no-password
```

Then open `Invoice - Maple & Oak.fmp12`.
