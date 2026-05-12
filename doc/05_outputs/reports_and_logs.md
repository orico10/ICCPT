# Reports and Logs

Reports and logs provide execution diagnostics and traceability.

## HTML report

`ReportGenerator.generate_html_report()` writes:

- `reports/report.html`

The report includes:

- processed file list
- captured errors and warnings
- execution timing details (when available)

## Logs

`config.yaml` currently defines:

- `logs/app.txt`
- `logs/error.log`

Log verbosity is controlled through `logs.level` in `config.yaml`.

## When to use them

- Troubleshoot failed runs.
- Review which files were loaded or skipped.
- Archive run metadata for audit or reproducibility.


