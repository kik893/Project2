import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
import numpy as np
import chardet
import requests
import sys
import argparse

# Configuration for LLM API Proxy
CONFIG = {
    "AI_PROXY_URL": "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
    "AIPROXY_TOKEN": os.getenv("AIPROXY_TOKEN", "INSERT_THE_AIPROXY_TOKEN"),  # Load token from environment
    "OUTPUT_DIR": os.path.dirname(os.path.abspath(__file__))
}

# Function to interact with LLM via AI Proxy
def ask_llm(question, context):
    try:
        headers = {"Authorization": f"Bearer {CONFIG['AIPROXY_TOKEN']}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": f"{question}\nContext:\n{context}"}]
        }
        response = requests.post(CONFIG["AI_PROXY_URL"], headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with AI Proxy: {e}")
        return "API Error: Unable to retrieve LLM response."

# Function to save visualizations
def visualization(plt, file_name):
    try:
        plt.tight_layout()
        plt.savefig(os.path.join(CONFIG["OUTPUT_DIR"], file_name), bbox_inches='tight')
        plt.close()
    except Exception as e:
        print(f"Error saving visualization {file_name}: {e}")

# Function to detect encoding with fallback
def detect_encoding(file_path):
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'  # Fallback to 'utf-8' if detection fails
        print(f"Detected file encoding: {encoding}")
        return encoding
    except Exception as e:
        print(f"Error detecting file encoding: {e}")
        return 'utf-8'  # Fallback to 'utf-8' as default

# Function to perform missing data analysis
def analyze_missing_data(df):
    missing_data = df.isnull().sum()
    missing_percent = (missing_data / len(df)) * 100
    missing_summary = missing_percent[missing_percent > 0].sort_values(ascending=False)
    plt.figure(figsize=(10, 6))
    missing_summary.plot(kind='bar', color='skyblue')
    plt.title("Percentage of Missing Data by Column")
    plt.ylabel("Percentage")
    visualization(plt, "missing_data.png")
    return missing_summary

# Function to perform correlation analysis
def analyze_correlation(df):
    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        correlation_matrix = numeric_df.corr()
        plt.figure(figsize=(10, 6))
        sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm")
        plt.title("Correlation Heatmap")
        visualization(plt, "correlation_heatmap.png")
        return correlation_matrix
    return None

# Function to detect outliers
def detect_outliers(df):
    numerical_cols = df.select_dtypes(include=[np.number])
    outlier_summary = {}
    for col in numerical_cols.columns:
        q1 = numerical_cols[col].quantile(0.25)
        q3 = numerical_cols[col].quantile(0.75)
        iqr = q3 - q1
        outliers = numerical_cols[(numerical_cols[col] < (q1 - 1.5 * iqr)) | (numerical_cols[col] > (q3 + 1.5 * iqr))]
        outlier_summary[col] = len(outliers)
    return outlier_summary

# Function to perform clustering analysis
def perform_clustering(df):
    numerical_cols = df.select_dtypes(include=[np.number])
    if not numerical_cols.empty:
        if numerical_cols.shape[1] >= 2:
            kmeans = KMeans(n_clusters=3, random_state=42)
            df['Cluster'] = kmeans.fit_predict(numerical_cols.fillna(0))
            plt.figure(figsize=(10, 6))
            sns.scatterplot(
                x=numerical_cols.columns[0],
                y=numerical_cols.columns[1],
                hue='Cluster',
                data=df,
                palette='viridis'
            )
            plt.title("Cluster Visualization")
            visualization(plt, "clusters.png")
            return df['Cluster'].value_counts()
    print("Not enough numerical columns for clustering.")
    return None

# Function to analyze distribution of numerical columns
def analyze_distribution(df):
    numerical_cols = df.select_dtypes(include=[np.number])
    for col in numerical_cols.columns:
        plt.figure(figsize=(10, 6))
        sns.histplot(df[col], kde=True, bins=30, color="blue")
        plt.title(f"Distribution of {col}")
        plt.xlabel(col)
        plt.ylabel("Frequency")
        visualization(plt, f"{col}_distribution.png")

# Function to generate the README file using LLM
def generate_readme(df, missing_summary, correlation_matrix, outlier_summary, clustering_summary):
    analysis_context = f"""
    Data Overview:
    The dataset contains {df.shape[0]} rows and {df.shape[1]} columns. It includes the following columns: {', '.join(df.columns)}.

    Missing Data:
    {missing_summary}

    Correlation Matrix:
    {correlation_matrix}

    Outliers Detected:
    {outlier_summary}

    Clustering Summary:
    {clustering_summary}
    """

    story = ask_llm("Write a story based on the dataset analysis, including key findings and implications.", analysis_context)
    dynamic_analysis = ask_llm("Based on the findings so far, suggest any further analysis or insights that should be explored.", analysis_context)
    
    try:
        with open(os.path.join(CONFIG["OUTPUT_DIR"], "README.md"), "w") as f:
            f.write("# Data Analysis Report\n\n")
            f.write("## Data Overview\n")
            f.write(f"The dataset contains {df.shape[0]} rows and {df.shape[1]} columns. It includes the following columns: {', '.join(df.columns)}.\n\n")
            f.write("## Missing Data\n")
            f.write(f"{missing_summary}\n\n")
            f.write("## Correlation Matrix\n")
            f.write(f"{correlation_matrix}\n\n")
            f.write("## Outliers\n")
            f.write(f"{outlier_summary}\n\n")
            f.write("## Clustering\n")
            f.write(f"{clustering_summary}\n\n")
            f.write("## Dynamic Insights\n")
            f.write(f"{dynamic_analysis}\n\n")
            f.write("## Story-based Summary\n")
            f.write(story)
        print("README.md file created successfully.")
    except Exception as e:
        print(f"Error creating README.md file: {e}")

# Main function to analyze the dataset and generate the report
def analyze_data(file_path):
    encoding = detect_encoding(file_path)
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        print(f"Loaded dataset {file_path} with {df.shape[0]} rows and {df.shape[1]} columns.")
    except UnicodeDecodeError as e:
        print(f"Unicode decode error: {e}")
        print("Retrying with 'ISO-8859-1' encoding as fallback...")
        df = pd.read_csv(file_path, encoding='ISO-8859-1')
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        sys.exit(1)

    # Proceed with analysis if the file loads successfully
    missing_summary = analyze_missing_data(df)
    correlation_matrix = analyze_correlation(df)
    outlier_summary = detect_outliers(df)
    clustering_summary = perform_clustering(df)
    analyze_distribution(df)
    generate_readme(df, missing_summary, correlation_matrix, outlier_summary, clustering_summary)

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a dataset and generate insights.")
    parser.add_argument("file_path", type=str, help="Path to the CSV file to analyze")
    args = parser.parse_args()

    if os.path.exists(args.file_path):
        analyze_data(args.file_path)
    else:
        print(f"File not found: {args.file_path}")
