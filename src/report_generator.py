from xml.etree.ElementTree import Element, SubElement, tostring
import os
from src import config
import logging
from jinja2 import Template
from datetime import timedelta


class ReportGenerator:
    warnings = []
    @staticmethod
    def generate_xml_report(headers=None, data=None, errors=None):
        """Generates an XML report at the defined path."""
        report_path = config["path"]["reports"]
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        # Create XML structure
        root = Element("Report")

        if headers:
            headers_element = SubElement(root, "Headers")
            for header in headers:
                SubElement(headers_element, "Header").text = header

        if data:
            data_element = SubElement(root, "Data")
            for row in data:
                row_element = SubElement(data_element, "Row")
                for cell in row:
                    SubElement(row_element, "Cell").text = str(cell)

        if errors:
            errors_element = SubElement(root, "Errors")
            for error in errors:
                SubElement(errors_element, "Error").text = str(error)

        # Guardar XML en archivo
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(tostring(root, encoding="unicode"))

        logging.info(f"Report generated: {report_path}")



    @staticmethod
    def add_warning(message):
        """Adds a warning to the report."""
        ReportGenerator.warnings.append(message)
        logging.warning(message)

    @staticmethod
    def generate_html_report(headers, data, errors, total_execution_time=None, building_load_time=None):
        """Generates an HTML report."""
        report_path = config["path"]["reports"]
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("<html><head><title>Report</title></head><body>")
                f.write("<h1>Results Report</h1>")

                if total_execution_time is not None:
                    f.write(f"<p><strong>Total execution time :</strong> {str(timedelta(seconds=total_execution_time))}</p>")

                if building_load_time is not None:
                    f.write(f"<p><strong>Time loading buildings file:</strong> {str(timedelta(seconds=building_load_time))}</p>")

                f.write("<h2>Processed Data</h2>")
                f.write("<table border='1'>")
                f.write("<tr>" + "".join(f"<th>{header}</th>" for header in headers) + "</tr>")
                for row in data:
                    f.write("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
                f.write("</table>")

                f.write("<h2>Errors</h2>")
                f.write("<ul>")
                for error in errors:
                    f.write(f"<li>{error}</li>")
                f.write("</ul>")

                f.write("<h2>Warnings</h2>")
                f.write("<ul>")
                for warning in ReportGenerator.warnings:
                    f.write(f"<li>{warning}</li>")
                f.write("</ul>")

                f.write("</body></html>")
            logging.info(f"HTML Report generated in: {report_path}")
        except Exception as e:
            logging.critical(f"Error generating HTML report: {e}")
            raise