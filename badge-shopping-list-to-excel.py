#! /usr/bin/env python3

import pdfplumber
import pandas as pd


def extract_tables_from_pdf(pdf_path, output_excel_path):
    # Open the PDF file
    with pdfplumber.open(pdf_path) as pdf:
        # Initialize an empty list to hold the DataFrames
        dfs = []

        # Loop through each page
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract tables from the page
            tables = page.extract_tables()

            # Convert each table into a DataFrame
            for table in tables:
                # Create a DataFrame
                # table[0] is header row
                df = pd.DataFrame(table[1:], columns=table[0])

                # Filter the DataFrame to include only "Badge" and "Required" columns
                if 'Badge' in df.columns and 'Required' in df.columns:
                    dfs.append(df[['Badge', 'Required']])

        # Concatenate all the DataFrames into one
        combined_df = pd.concat(dfs, ignore_index=True)

        # Save the combined DataFrame to an Excel file
        combined_df.to_excel(output_excel_path, index=False)


# Example usage:
pdf_path = "/Users/tom.kivlin/Downloads/Badge Shopping List.pdf"  # Path to your PDF file
# Path to save the Excel file
output_excel_path = "/Users/tom.kivlin/Downloads/Badge Shopping List.xlsx"
extract_tables_from_pdf(pdf_path, output_excel_path)
