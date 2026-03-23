import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="RTA Dashboard & Logistics Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS STYLING
# ============================================================================
st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 0.5rem;
        }
        .section-header {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 0.5rem;
        }
        .metric-card {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .on-site-badge {
            background-color: #d4edda;
            color: #155724;
            padding: 0.25rem 0.75rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }
        .wah-badge {
            background-color: #cce5ff;
            color: #004085;
            padding: 0.25rem 0.75rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }
        .rest-badge {
            background-color: #f5f5f5;
            color: #666;
            padding: 0.25rem 0.75rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING AND PROCESSING
# ============================================================================
@st.cache_data
def load_data():
    """Load and process the Excel data."""
    file_path = '/home/ubuntu/upload/DATAassessement.xlsx'
    
    # Load schedules
    schedules_raw = pd.read_excel(file_path, sheet_name='W14 schedule', header=None)
    
    # Extract dates from row 0
    dates = []
    for i in range(3, schedules_raw.shape[1], 2):
        if pd.notna(schedules_raw.iloc[0, i]):
            date_val = schedules_raw.iloc[0, i]
            if isinstance(date_val, (pd.Timestamp, datetime)):
                dates.append(date_val.date())
            else:
                dates.append(date_val)
    
    # Extract schedules data starting from row 3
    schedules_data = schedules_raw.iloc[3:].copy()
    schedules_data.columns = schedules_raw.iloc[2]
    schedules_data = schedules_data.reset_index(drop=True)
    
    # Load credentials
    credentials = pd.read_excel(file_path, sheet_name='Credentials')
    
    return schedules_data, credentials, dates

def process_schedule_data(schedules_data, credentials, dates):
    """Process schedule data into a usable format."""
    # Merge schedules with credentials
    merged_data = schedules_data.merge(credentials, on='MAT', how='left')
    
    # Create a list to store processed schedule records
    schedule_records = []
    
    for idx, row in merged_data.iterrows():
        manager = row['Manager']
        full_name = row['Names']
        mat = row['MAT']
        phone = row['Phone ']
        address = row['Adresse exacte']
        location = row['Localisation']
        boucle = row['Boucle']
        
        # Process each day's schedule
        for day_idx, date_obj in enumerate(dates):
            shift_in_col = f'I' if day_idx == 0 else f'I {day_idx + 1}'
            shift_out_col = f'O' if day_idx == 0 else f'O {day_idx + 1}'
            
            shift_in = row.get(shift_in_col, '')
            shift_out = row.get(shift_out_col, '')
            
            # Determine work location based on shift
            work_location = 'Rest/Off'
            if pd.notna(shift_in) and shift_in not in ['R', 'CP', '']:
                work_location = 'On-Site'
            elif pd.notna(shift_in) and shift_in == 'CP':
                work_location = 'Leave (CP)'
            elif pd.notna(shift_in) and shift_in == 'R':
                work_location = 'Rest/Off'
            
            schedule_records.append({
                'Date': date_obj,
                'MAT': mat,
                'Full Name': full_name,
                'Manager': manager,
                'Phone': phone,
                'Address': address,
                'Localisation': location,
                'Boucle': boucle,
                'Shift In': shift_in,
                'Shift Out': shift_out,
                'Work Location': work_location
            })
    
    return pd.DataFrame(schedule_records)

# ============================================================================
# REFLECTOR (AUDIT LOG) MANAGEMENT
# ============================================================================
def get_reflector_data():
    """Get or initialize the reflector (audit log) data."""
    if 'reflector_data' not in st.session_state:
        st.session_state.reflector_data = []
    return st.session_state.reflector_data

def log_to_reflector(mat, full_name, manager, date_obj, address, work_location):
    """Log a search/selection to the reflector."""
    reflector_data = get_reflector_data()
    reflector_data.append({
        'Timestamp': datetime.now(),
        'MAT': mat,
        'Full Name': full_name,
        'Manager': manager,
        'Date': date_obj,
        'Address': address,
        'Work Location': work_location
    })
    st.session_state.reflector_data = reflector_data

# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    # Load data
    schedules_data, credentials, dates = load_data()
    schedule_df = process_schedule_data(schedules_data, credentials, dates)
    
    # ========================================================================
    # HEADER
    # ========================================================================
    st.markdown('<div class="main-header">📊 RTA User Dashboard & Logistics Tracker</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # ========================================================================
    # SIDEBAR - GLOBAL FILTERS
    # ========================================================================
    st.sidebar.markdown("### 🔍 Global Filters")
    
    # Date filter
    selected_date = st.sidebar.selectbox(
        "Select Date",
        options=sorted(schedule_df['Date'].unique()),
        format_func=lambda x: x.strftime('%A, %B %d, %Y')
    )
    
    # Manager filter
    managers = sorted(schedule_df['Manager'].dropna().unique())
    selected_manager = st.sidebar.selectbox(
        "Select Team Leader (Manager)",
        options=['All'] + managers
    )
    
    # Agent filter
    if selected_manager == 'All':
        agents = sorted(schedule_df['Full Name'].dropna().unique())
    else:
        agents = sorted(schedule_df[schedule_df['Manager'] == selected_manager]['Full Name'].dropna().unique())
    
    selected_agent = st.sidebar.selectbox(
        "Select Agent (MAT)",
        options=['All'] + agents,
        format_func=lambda x: x if x == 'All' else f"{x}"
    )
    
    # ========================================================================
    # FILTER DATA BASED ON SELECTIONS
    # ========================================================================
    filtered_df = schedule_df[schedule_df['Date'] == selected_date].copy()
    
    if selected_manager != 'All':
        filtered_df = filtered_df[filtered_df['Manager'] == selected_manager]
    
    if selected_agent != 'All':
        filtered_df = filtered_df[filtered_df['Full Name'] == selected_agent]
    
    # ========================================================================
    # TAB 1: AGENT DASHBOARD
    # ========================================================================
    tab1, tab2, tab3 = st.tabs(["👥 Agent Dashboard", "🚚 Logistics & Transport", "📋 Reflector (Audit Log)"])
    
    with tab1:
        st.markdown('<div class="section-header">Agent Shift Schedule & Work Location</div>', unsafe_allow_html=True)
        
        if len(filtered_df) == 0:
            st.warning("No agents found matching the selected filters.")
        else:
            # Create interactive table
            display_cols = ['Full Name', 'MAT', 'Manager', 'Shift In', 'Shift Out', 'Work Location', 'Address', 'Phone']
            display_df = filtered_df[display_cols].copy()
            
            # Add work location selector
            st.subheader("Modify Work Location")
            
            for idx, row in filtered_df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                
                with col1:
                    st.write(f"**{row['Full Name']}** (MAT: {row['MAT']})")
                
                with col2:
                    st.write(f"Shift: {row['Shift In']} - {row['Shift Out']}")
                
                with col3:
                    work_location_options = ['On-Site', 'Work-at-Home (W@H)', 'Rest/Off', 'Leave (CP)']
                    selected_location = st.selectbox(
                        f"Location for {row['MAT']}",
                        options=work_location_options,
                        index=work_location_options.index(row['Work Location']) if row['Work Location'] in work_location_options else 0,
                        key=f"location_{row['MAT']}"
                    )
                
                with col4:
                    if st.checkbox(f"Log {row['MAT']}", key=f"log_{row['MAT']}"):
                        log_to_reflector(
                            mat=row['MAT'],
                            full_name=row['Full Name'],
                            manager=row['Manager'],
                            date_obj=row['Date'],
                            address=row['Address'],
                            work_location=selected_location
                        )
                        st.success(f"✓ Logged {row['Full Name']}")
            
            # Display detailed schedule table
            st.subheader("Detailed Schedule Information")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # TAB 2: LOGISTICS & TRANSPORT
    # ========================================================================
    with tab2:
        st.markdown('<div class="section-header">Weekly Transport Requirements & KPIs</div>', unsafe_allow_html=True)
        
        # Filter for the entire week
        week_df = schedule_df.copy()
        
        # Identify shifts that qualify for transport (08:00, 09:00, 10:00)
        transport_eligible_shifts = ['08:00:00', '09:00:00', '10:00:00']
        
        # Count on-site agents by day
        on_site_by_day = []
        wah_by_day = []
        days_list = []
        
        for day in sorted(schedule_df['Date'].unique()):
            day_data = week_df[week_df['Date'] == day]
            
            # Count On-Site agents
            on_site_count = len(day_data[day_data['Work Location'] == 'On-Site'])
            
            # Count Work-at-Home agents
            wah_count = len(day_data[day_data['Work Location'] == 'Work-at-Home (W@H)'])
            
            on_site_by_day.append(on_site_count)
            wah_by_day.append(wah_count)
            days_list.append(day.strftime('%a, %b %d'))
        
        # Create visualization
        col1, col2 = st.columns(2)
        
        with col1:
            # On-Site vs W@H by day
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Bar(
                x=days_list,
                y=on_site_by_day,
                name='On-Site',
                marker_color='#28a745'
            ))
            fig_daily.add_trace(go.Bar(
                x=days_list,
                y=wah_by_day,
                name='Work-at-Home',
                marker_color='#007bff'
            ))
            fig_daily.update_layout(
                title='Daily Agent Distribution',
                xaxis_title='Date',
                yaxis_title='Number of Agents',
                barmode='group',
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            # Weekly totals pie chart
            total_on_site = sum(on_site_by_day)
            total_wah = sum(wah_by_day)
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=['On-Site', 'Work-at-Home'],
                values=[total_on_site, total_wah],
                marker=dict(colors=['#28a745', '#007bff']),
                hoverinfo='label+value+percent'
            )])
            fig_pie.update_layout(
                title='Weekly On-Site vs W@H Distribution',
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # KPIs
        st.markdown('<div class="section-header">Key Performance Indicators (KPIs)</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Weekly On-Site",
                value=total_on_site,
                delta=f"{(total_on_site / (total_on_site + total_wah) * 100):.1f}%" if (total_on_site + total_wah) > 0 else "0%"
            )
        
        with col2:
            st.metric(
                label="Total Weekly W@H",
                value=total_wah,
                delta=f"{(total_wah / (total_on_site + total_wah) * 100):.1f}%" if (total_on_site + total_wah) > 0 else "0%"
            )
        
        with col3:
            avg_on_site = np.mean(on_site_by_day) if on_site_by_day else 0
            st.metric(
                label="Avg Daily On-Site",
                value=f"{avg_on_site:.1f}",
                delta="agents/day"
            )
        
        with col4:
            avg_wah = np.mean(wah_by_day) if wah_by_day else 0
            st.metric(
                label="Avg Daily W@H",
                value=f"{avg_wah:.1f}",
                delta="agents/day"
            )
        
        # Transport Boucles Analysis
        st.markdown('<div class="section-header">Transport Boucles Analysis</div>', unsafe_allow_html=True)
        
        # Count agents by Boucle and work location
        boucle_analysis = week_df[week_df['Work Location'] == 'On-Site'].groupby('Boucle').size().reset_index(name='Count')
        boucle_analysis = boucle_analysis.sort_values('Count', ascending=False)
        
        if len(boucle_analysis) > 0:
            fig_boucles = px.bar(
                boucle_analysis,
                x='Boucle',
                y='Count',
                title='On-Site Agents by Transport Boucle',
                labels={'Count': 'Number of Agents', 'Boucle': 'Boucle (Transport Route)'},
                color='Count',
                color_continuous_scale='Blues'
            )
            fig_boucles.update_layout(height=400)
            st.plotly_chart(fig_boucles, use_container_width=True)
            
            st.dataframe(boucle_analysis, use_container_width=True, hide_index=True)
        else:
            st.info("No on-site agents found for the selected period.")
    
    # ========================================================================
    # TAB 3: REFLECTOR (AUDIT LOG)
    # ========================================================================
    with tab3:
        st.markdown('<div class="section-header">Reflector: Audit Log of All Selections</div>', unsafe_allow_html=True)
        
        reflector_data = get_reflector_data()
        
        if len(reflector_data) == 0:
            st.info("No selections logged yet. Use the Agent Dashboard to log selections.")
        else:
            reflector_df = pd.DataFrame(reflector_data)
            
            # Display the reflector table
            st.subheader("Complete Audit Trail")
            st.dataframe(reflector_df, use_container_width=True, hide_index=True)
            
            # Export reflector data
            csv = reflector_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Reflector Data as CSV",
                data=csv,
                file_name=f"reflector_audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Summary statistics
            st.subheader("Reflector Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Entries", len(reflector_df))
            
            with col2:
                st.metric("Unique Agents", reflector_df['MAT'].nunique())
            
            with col3:
                st.metric("Unique Managers", reflector_df['Manager'].nunique())

if __name__ == "__main__":
    main()
