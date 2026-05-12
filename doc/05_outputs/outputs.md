# Outputs and Reports

ICCPT writes both quick-look outputs and more detailed export files.

## Main output folders

The current `config.yaml` points to:

- `data/outputs`
- `data/summary_results`
- `reports`
- `logs`

## Summary results

See [Summary outputs](summary_outputs.md).

## Detailed outputs

See [Detailed outputs](detailed_outputs.md).

## Reports and logs

See [Reports and logs](reports_and_logs.md).

## Intended use of outputs

From the file names and export code, the outputs support at least:

- fast scenario QA
- dashboard ingestion
- visualization of adoption by area and technology
- annualized financial analysis

The existing README also suggests use in:

- Power BI
- Tableau
- GIS-compatible workflows

That is directionally consistent with the export layout, although a tested end-to-end dashboard integration guide is still `TODO`.

## Output caveats

- some exports are optional or commented out in the current code
- outputs may be overwritten by later runs
- the repository does not yet provide a complete schema dictionary for each generated TSV

## Recommended next step

Add one dedicated reference page for:

- each summary TSV
- each detailed TSV
- the meaning and units of every column
