# Contributing to Patchwork

Thanks for helping. FileMaker developers know things about FMUpgradeTool that no documentation says: every verified finding makes this tool better for everyone.

## Three easy ways to help

1. **Share a finding.** You noticed FMUpgradeTool skips a patch, or needs an attribute the docs don't mention? Open a [field guide finding](https://github.com/Abdeltoto/patchwork/issues/new?template=field-guide.yml). Say which FileMaker version, what you tried, what happened.
2. **Share a brand or a recipe.** A `brand.json` for another Claris starter theme, or a step-by-step patch recipe, goes in `examples/`.
3. **Fix or build.** Pick an issue labeled `good first issue`.

## Development

```bash
git clone https://github.com/Abdeltoto/patchwork
cd patchwork
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[image]"
python -m unittest discover -s tests
```

The tests use a small fixture export and a fake FMUpgradeTool, so they run anywhere, without FileMaker.

If you change how a patch is built, also run the end-to-end tests against the real Claris tools. They need the free [Invoice Solution](https://marketplace.claris.com/detail/2000.html), closed in FileMaker, and take about two minutes:

```bash
PATCHWORK_SAMPLE="/path/to/Invoice Solution.fmp12" python -m unittest discover -s tests -p test_integration.py -v
# Windows: $env:PATCHWORK_SAMPLE = "C:\path\to\Invoice Solution.fmp12"
```

They work on a copy and check the content of every change, not only that FMUpgradeTool reported success (it reports success while skipping changes, or dropping a formula it cannot parse). Say in the pull request that they pass, and add a scenario for any new operation.

## Rules

- Standard library only at runtime. Pillow stays optional.
- Never commit a `.fmp12`, an export, or anything from a customer file. Fixtures are hand-written and fictional.
- One topic per pull request, with a test.
- Error messages say what to do next, in one line.

By contributing you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and to license your work under the [MIT License](LICENSE).
