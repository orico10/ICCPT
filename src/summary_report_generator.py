# from summary_report import SummaryReport
# Example usage:


# data = {
#     "econ": [
#         {"Plan": "Base", "Health": 1.00, "TI_Gender": 1.00, "Emissions": 1.00, "Deforest": 1.00},
#         {"Plan": "Plan 1 - Prices", "Health": 0.99, "TI_Gender": 0.99, "Emissions": 0.97, "Deforest": 0.97},
#         {"Plan": "Plan 1 - Prices+Infra+Growth", "Health": 0.86, "TI_Gender": 0.70, "Emissions": 0.53, "Deforest": 0.52},
#         {"Plan": "Plan 2 - Prices", "Health": 0.85, "TI_Gender": 0.70, "Emissions": 0.53, "Deforest": 0.52},
#         {"Plan": "Plan 2 - Prices+Infra+Growth", "Health": 0.81, "TI_Gender": 0.66, "Emissions": 0.52, "Deforest": 0.45},
#     ],
#     "balance": [
#         {"Plan": "Base", "Economic": 0.787, "Social": 0.893},
#         {"Plan": "Plan 1 - Prices", "Economic": 0.603, "Social": 0.791},
#         {"Plan": "Plan 1 - Prices+Infra+Growth", "Economic": 0.710, "Social": 0.710},
#         {"Plan": "Plan 2 - Prices", "Economic": 0.196, "Social": 0.423},
#         {"Plan": "Plan 2 - Prices+Infra+Growth", "Economic": -0.599, "Social": 0.006},
#     ],
#     "cooking": [
#         {"Year": "2023", "Scenario": "Base", "Rural %": 6.68, "Urban %": 25.35, 
#          "Cost_Rural_$/Cook": 0.058, "Cost_Rural_S$/Year": 105.30,
#          "Cost_Urban_$/Cook": 0.089, "Cost_Urban_S$/Year": 180.94, "Incr %": 0},
        
#         {"Year": "2026", "Scenario": "Plan 1", "Rural %": 10.40, "Urban %": 28.74, 
#          "Cost_Rural_$/Cook": 0.061, "Cost_Rural_S$/Year": 110.79,
#          "Cost_Urban_$/Cook": 0.104, "Cost_Urban_S$/Year": 189.18, "Incr %": 5.2},

#         {"Year": "2029", "Scenario": "Plan 1 + Infra + Growth", "Rural %": 68.77, "Urban %": 84.46, 
#          "Cost_Rural_$/Cook": 0.053, "Cost_Rural_S$/Year": 97.03,
#          "Cost_Urban_$/Cook": 0.088, "Cost_Urban_S$/Year": 161.15, "Incr %": -14.8},

#         {"Year": "2029", "Scenario": "Plan 2", "Rural %": 68.52, "Urban %": 84.65, 
#          "Cost_Rural_$/Cook": 0.064, "Cost_Rural_S$/Year": 116.86,
#          "Cost_Urban_$/Cook": 0.097, "Cost_Urban_S$/Year": 174.08, "Incr %": -3.8},

#         {"Year": "2034", "Scenario": "Plan 2 + Infra + Growth", "Rural %": 68.79, "Urban %": 90.61, 
#          "Cost_Rural_$/Cook": 0.072, "Cost_Rural_S$/Year": 130.52,
#          "Cost_Urban_$/Cook": 0.111, "Cost_Urban_S$/Year": 201.79, "Incr %": 11.7},
#     ]
# }

# report = SummaryReport(data)
# report.generate()