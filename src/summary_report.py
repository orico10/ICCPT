import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os

class SummaryReport:
    def __init__(self, summary_data: dict, output_dir: str = "./output"):
        self.data = summary_data
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Cargar plantilla desde el mismo directorio del script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.env = Environment(loader=FileSystemLoader(searchpath=current_dir))

    def render_html(self):
        econ_html = pd.DataFrame(self.data["econ"]).to_html(index=False, classes="styled-table")
        balance_html = pd.DataFrame(self.data["balance"]).to_html(index=False, classes="styled-table")
        cooking_html = pd.DataFrame(self.data["cooking"]).to_html(index=False, classes="styled-table")

        template = self.env.get_template("report_template.html")  # usa esta plantilla
        html_out = template.render(
            title="Summary Results Report",
            econ_table=econ_html,
            balance_table=balance_html,
            cooking_table=cooking_html
        )

        out_path = os.path.join(self.output_dir, "summary_report.html")
        with open(out_path, "w") as f:
            f.write(html_out)
        print(f"✅ Report generated at: {out_path}")

    def generate(self):
        self.render_html()
