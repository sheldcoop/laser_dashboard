import streamlit as st
import pandas as pd
import io

# This is our reusable "master toolkit" function.
# Its only job is to create a download section for any DataFrame we give it.

def create_download_hub(df: pd.DataFrame, file_prefix: str):
    """
    Renders a multi-format download hub for a given DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to be downloaded.
        file_prefix (str): The prefix for the downloaded file name (e.g., "fluence_results").
    """
    st.markdown("---")
    st.subheader("Download Options")

    # Use columns for a clean layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Let the user choose the format
        format_choice = st.radio(
            "Select Format", 
            ["CSV", "Excel", "JSON"], # Sticking to robust data formats
            horizontal=True, 
            label_visibility="collapsed",
            key=f"{file_prefix}_format" # A unique key prevents widget conflicts
        )

    with col2:
        # Prepare the data and button based on the user's choice
        if format_choice == "CSV":
            # Convert DataFrame to CSV string
            file_data = df.to_csv(index=False).encode('utf-8')
            mime_type = "text/csv"
            file_ext = "csv"
        
        elif format_choice == "Excel":
            # Convert DataFrame to an in-memory Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
            file_data = output.getvalue()
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_ext = "xlsx"

        elif format_choice == "JSON":
            # Convert DataFrame to a JSON string
            file_data = df.to_json(orient='records', indent=4).encode('utf-8')
            mime_type = "application/json"
            file_ext = "json"

        # Create the download button with the prepared data
        st.download_button(
            label=f"Download as {format_choice}",
            data=file_data,
            file_name=f"{file_prefix}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}",
            mime=mime_type,
            use_container_width=True
        )
