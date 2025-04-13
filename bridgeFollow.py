import streamlit as st
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup

def app():
    # Set page config to wide layout
    st.set_page_config(page_title="Bridge Competition Rankings", layout="wide")
    
    # Initialize session states
    if 'results_url' not in st.session_state:
        st.session_state.results_url = None
    if 'teams_data' not in st.session_state:
        st.session_state.teams_data = None
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'show_round' not in st.session_state:
        st.session_state.show_round = False
    if 'current_round_index' not in st.session_state:
        st.session_state.current_round_index = -1
    if 'event_title' not in st.session_state:
        st.session_state.event_title = "Bridge Competition Rankings"
    if 'all_games_data' not in st.session_state:
        st.session_state.all_games_data = []
    if 'scraping_progress' not in st.session_state:
        st.session_state.scraping_progress = 0
    if 'cache_timestamp' not in st.session_state:
        st.session_state.cache_timestamp = None
    if 'view_games' not in st.session_state:
        st.session_state.view_games = None
    if 'selected_team' not in st.session_state:
        st.session_state.selected_team = "Select a team to follow"
    if 'viewed_team' not in st.session_state:
        st.session_state.viewed_team = None
    if 'viewed_match' not in st.session_state:
        st.session_state.viewed_match = None
    if 'viewed_competitor' not in st.session_state:
        st.session_state.viewed_competitor = None
    if 'viewed_match_VPs' not in st.session_state:
        st.session_state.viewed_match_VPs = None
    if 'viewing_games' not in st.session_state:
        st.session_state.viewing_games = False

    # Set up CSS
    st.markdown("""
    <style>
        .main-title { color: #2c3e50; text-align: center; font-family: Arial, sans-serif; }
        .round-title { color: #2c3e50; text-align: center; animation: fadeIn 1s ease-in; font-family: Arial, sans-serif; }
        .results-link { color: #3498db; text-align: center; display: block; margin-bottom: 20px; font-family: Arial, sans-serif; }
        .stButton > button { display: inline-flex; font-family: Arial, sans-serif; }
        .highlighted { background-color: yellow !important; }
        .stDataFrame { width: 100% !important; }
        .stDataFrame th, .stDataFrame td { text-align: left !important; font-family: Arial, sans-serif !important; }
        .success-message { color: green; text-align: center; font-family: Arial, sans-serif; }
        .error-message { color: red; text-align: center; font-family: Arial, sans-serif; }
        .progress-text { text-align: center; font-family: Arial, sans-serif; margin-bottom: 10px; }
        .back-link {
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
            margin-bottom: 20px;
            display: block;
            font-family: Arial, sans-serif;
        }
        .back-link:hover {
            text-decoration: underline;
        }
        .back-button {
            background-color: transparent;
            border: none;
            color: #3498db;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            font-weight: bold;
            font-family: Arial, sans-serif;
        }
        .back-button:hover {
            text-decoration: underline;
        }
    </style>
    """, unsafe_allow_html=True)

    # Scrape team data
    def scrape_team_data(url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            event_info = soup.find('table', {'class': 'eventInfo'})
            if event_info:
                title_row = event_info.find('tr', {'class': 'eventInfoTitle'})
                if title_row:
                    st.session_state.event_title = title_row.find('td').text.strip()
            
            table = soup.find('table', {'class': 'resultsTable'})
            
            if not table:
                st.error("Could not find results table in the page")
                return None
                
            teams_data = []
            
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) < 5:
                    continue
                
                name_link = cols[1].find('a')
                name = name_link.text.strip() if name_link else cols[1].text.strip()
                personal_url = name_link['href'] if name_link and name_link.has_attr('href') else None
                
                matches = []
                for col in cols[4:32]:
                    bdo = col.find('bdo')
                    if bdo:
                        match_score_text = bdo.text.strip().replace(',', '.')
                        try:
                            matches.append(float(match_score_text))
                        except ValueError:
                            matches.append(0.0)
                    else:
                        matches.append(0.0)
                
                penalty_col = cols[-1].find('bdo')
                penalty = 0.0
                if penalty_col:
                    penalty_text = penalty_col.text.strip().replace(',', '.').replace(' ', '')
                    if penalty_text and penalty_text != '.':
                        try:
                            penalty = float(penalty_text)
                        except ValueError:
                            penalty = 0.0
                
                teams_data.append({
                    "name": name,
                    "matches": matches,
                    "penalty": penalty,
                    "personal_url": personal_url
                })
            
            return teams_data if teams_data else None
            
        except Exception as e:
            st.error(f"Error scraping data: {str(e)}")
            return None

    # Get match details
    def get_all_match_details(team_name, personal_url):
        if not personal_url:
            return []
        
        if 'debug_log' not in st.session_state:
            st.session_state.debug_log = []
        
        try:
            if personal_url.startswith('personal1.php'):
                full_url = f"https://www.bridge.co.il/viewer/{personal_url}"
            else:
                full_url = personal_url
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(full_url, headers=headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_games = []
            match_tables = soup.find_all('table', {'class': 'mpersonal'})
            st.session_state.debug_log.append(f"Team {team_name}: Found {len(match_tables)} match tables")
            
            for table in match_tables:
                match_link = table.find('a', href=lambda x: x and 'round=' in x)
                if not match_link:
                    st.session_state.debug_log.append(f"Team {team_name}: No match link in table")
                    continue
                
                try:
                    match_number = int(match_link['href'].split('round=')[1].split('&')[0])
                except:
                    st.session_state.debug_log.append(f"Team {team_name}: Failed to extract match number")
                    continue
                
                st.session_state.debug_log.append(f"Team {team_name}: Processing match {match_number}")
                
                rows = table.find_all('tr')
                start_index = 4
                game_rows = rows[start_index:]
                st.session_state.debug_log.append(f"Team {team_name}, Match {match_number}: Found {len(game_rows)} game rows")
                
                for row in game_rows:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        st.session_state.debug_log.append(f"Team {team_name}, Match {match_number}: Skipped row - {len(cols)} cols")
                        continue
                    
                    board = ""
                    for col in cols:
                        if 'rank' in col.get('class', []):
                            board_link = col.find('a')
                            board = board_link.text.strip() if board_link and any(c.isdigit() for c in board_link.text.strip()) else ""
                            break
                    if not board:
                        st.session_state.debug_log.append(f"Team {team_name}, Match {match_number}: Skipped row - no board")
                        continue
                    
                    contract = ""
                    for col in cols:
                        if 'contract' in col.get('class', []):
                            contract = col.get_text(strip=True)
                            break
                    
                    if not contract or 'NP' in contract.upper():
                        st.session_state.debug_log.append(f"Team {team_name}, Match {match_number}: Skipped row - no contract: '{contract}'")
                        continue
                    
                    lead = ""
                    for col in cols:
                        if 'lead' in col.get('class', []):
                            lead = col.find('bdo').get_text(strip=True) if col.find('bdo') else col.get_text(strip=True)
                            break
                    if not lead and len(cols) >= 3:
                        lead = cols[-3].get_text(strip=True)
                    
                    imp = ""
                    for col in cols:
                        if 'res' in col.get('class', []) and 'resns' not in col.get('class', []) and 'resew' not in col.get('class', []):
                            imp = col.get_text(strip=True)
                            break
                    
                    ns_score = cols[0].get_text(strip=True) if cols[0].get_text(strip=True) else ""
                    ew_score = cols[1].get_text(strip=True) if cols[1].get_text(strip=True) else ""
                    score = ns_score if ns_score else ew_score if ew_score else ""
                    
                    game_data = {
                        "team": team_name,
                        "match": match_number,
                        "board": board,
                        "contract": contract,
                        "score": score,
                        "imp": imp,
                        "lead": lead
                    }
                    all_games.append(game_data)
                    st.session_state.debug_log.append(f"Team {team_name}, Match {match_number}, Board {board}: Added game - contract={contract}, imp={imp}, lead={lead}, score={score}")
            
            st.session_state.debug_log.append(f"Team {team_name}: Total games collected: {len(all_games)}")
            return all_games
        except Exception as e:
            st.session_state.debug_log.append(f"Team {team_name}: Error - {str(e)}")
            return []

    # Conditional UI rendering
    if not st.session_state.data_loaded:
        # Initial GUI: URL input and buttons
        st.markdown(f"<h1 class='main-title'>Bridge Competition Rankings</h1>", unsafe_allow_html=True)
        default_url = "https://www.bridge.co.il/viewer/total1.php?event=26699"
        url_input = st.text_input("Enter results URL:", value=default_url)
        
        col_load, col_refresh = st.columns([1, 1])
        with col_load:
            load_button = st.button("Load")
        with col_refresh:              
            refresh_button = st.button("Refresh Data", disabled=True)  # Disabled until data is loaded
        
        # Cache handling and data loading
        if load_button:
            with st.spinner("Loading team data..."):
                scraped_data = scrape_team_data(url_input)
                if scraped_data:
                    st.session_state.teams_data = scraped_data
                    st.session_state.results_url = url_input
                    st.session_state.data_loaded = True
                    st.session_state.all_games_data = []
                    st.session_state.scraping_progress = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_teams = len(st.session_state.teams_data)
                    for i, team in enumerate(st.session_state.teams_data):
                        status_text.text(f"Loading match details for {team['name']} ({i+1}/{total_teams})")
                        games = get_all_match_details(team['name'], team['personal_url'])
                        st.session_state.all_games_data.extend(games)
                        st.session_state.scraping_progress = (i + 1) / total_teams
                        progress_bar.progress(st.session_state.scraping_progress)
                    
                    progress_bar.empty()
                    status_text.empty()
                    st.session_state.cache_timestamp = time.time()
                    st.markdown("<p class='success-message'>Data loaded successfully!</p>", unsafe_allow_html=True)
                    st.rerun()  # Rerun to switch to main GUI
                else:
                    st.markdown("<p class='error-message'>Failed to load data. Please check the URL.</p>", unsafe_allow_html=True)
    else:
        # Main GUI: Competition interface
        # Display event title
        st.markdown(f"<h1 class='main-title'>{st.session_state.event_title}</h1>", unsafe_allow_html=True)
        
        # Display results link
        if st.session_state.results_url:
            st.markdown(f"<a href='{st.session_state.results_url}' target='_blank' class='results-link'>View Actual Results</a>", unsafe_allow_html=True)
        
        # Main UI
        if st.session_state.teams_data:
            matches_per_day = 7
            rounds = []
            for day in range(1, 5):
                for match in range(1, matches_per_day + 1):
                    start_match = (day - 1) * matches_per_day + match
                    rounds.append(f"Day {day} - Match {start_match}")
            
            # Calculate rankings
            def calculate_rankings(round_index):
                if round_index < 0:
                    return None, -1
                
                current_match = min(round_index, len(rounds) - 1)
                
                match_vps = []
                for team in st.session_state.teams_data:
                    match_vps.append({
                        "name": team["name"],
                        "vp": team["matches"][current_match] if current_match < len(team["matches"]) else 0
                    })
                
                match_vps_sorted = sorted(match_vps, key=lambda x: x["vp"], reverse=True)
                paired_teams = []
                temp_match_vps = match_vps_sorted.copy()
                
                while temp_match_vps:
                    if len(temp_match_vps) == 1:
                        paired_teams.append([temp_match_vps[0], {"name": "Unknown", "vp": 0}])
                        break
                    highest = temp_match_vps.pop(0)
                    lowest = temp_match_vps.pop(-1)
                    paired_teams.append([highest, lowest])
                
                teams_display = []
                for team in st.session_state.teams_data:
                    total_vps = sum(team["matches"][:current_match+1]) + team.get("penalty", 0)
                    
                    competitor = "Unknown"
                    for pair in paired_teams:
                        if pair[0]["name"] == team["name"]:
                            competitor = pair[1]["name"]
                            break
                        elif pair[1]["name"] == team["name"]:
                            competitor = pair[0]["name"]
                            break
                    
                    teams_display.append({
                        "name": team["name"],
                        "matchVPs": team["matches"][current_match] if current_match < len(team["matches"]) else 0,
                        "totalVPs": total_vps,
                        "competitor": competitor
                    })
                
                teams_display.sort(key=lambda x: x["totalVPs"], reverse=True)
                
                df = pd.DataFrame(teams_display)
                df.insert(0, "Position", range(1, len(df) + 1))
                df["View Games"] = "View Games"
                df.columns = ["Position", "Team", "Match VPs", "Total VPs", "Competitor", ""]
                
                df["Match VPs"] = df["Match VPs"].map(lambda x: f"{x:.2f}")
                df["Total VPs"] = df["Total VPs"].map(lambda x: f"{x:.2f}")
                
                return df, current_match
            
            # Handle View Games click
            def display_games_table(team, match, competitor, match_vps):
                if st.button("← Back to Matches", key=f"back_button_{team}_{match}"):
                    st.session_state.viewing_games = False
                    st.rerun()
                
                games = [g for g in st.session_state.all_games_data if g["team"] == team and g["match"] == match + 1]
                if games:
                    st.markdown(f"<h3>Games for Match {match + 1}</h3><h4>{team} ({round(float(match_vps),2)} VP) - VS - {competitor} ({round(20-float(match_vps),2)} VP)</h4>", unsafe_allow_html=True)
                    games_df = pd.DataFrame(games)[["board", "contract", "score", "imp", "lead"]]
                    games_df.columns = ["Board", "Contract", "Score", "IMP", "Lead"]
                    st.dataframe(
                        games_df,
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.markdown(f"<p>No games found for {team} in Match {match + 1}</p>", unsafe_allow_html=True)
            
            # Display either games view or matches view
            if st.session_state.viewing_games and st.session_state.viewed_team is not None and st.session_state.viewed_match is not None:
                display_games_table(st.session_state.viewed_team, st.session_state.viewed_match, st.session_state.viewed_competitor, st.session_state.viewed_match_VPs)
            else:
                # Control panel
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    team_options = ["Select a team to follow"] + [team["name"] for team in st.session_state.teams_data]
                    selected_team = st.selectbox("Team to follow:", team_options, index=team_options.index(st.session_state.selected_team), key="team_select_unique")
                    st.session_state.selected_team = selected_team
                
                with col2:
                    st.markdown("<br/>", unsafe_allow_html=True)
                    if st.button("Next Match", disabled=st.session_state.current_round_index >= len(rounds) - 1, key="next_match_button"):
                        if st.session_state.current_round_index == -1:
                            st.session_state.current_round_index = 0
                        else:
                            st.session_state.current_round_index += 1
                        st.session_state.show_round = True
                
                # Render round and table
                if st.session_state.show_round:
                    round_title = rounds[min(st.session_state.current_round_index, len(rounds)-1)]
                    st.markdown(f"<h2 class='round-title'>Round: {round_title}</h2>", unsafe_allow_html=True)
                    
                    df, current_match = calculate_rankings(st.session_state.current_round_index)
                    
                    if df is not None:
                        def highlight_selected_team(team):
                            return 'background-color: yellow' if team == st.session_state.selected_team and st.session_state.selected_team != "Select a team to follow" else ''
                        
                        st.markdown("""
                        <style>
                            .stDataFrame { width: 100% !important; }
                            .stDataFrame table { border-collapse: collapse; font-family: Arial, sans-serif; }
                            .stDataFrame th, .stDataFrame td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                            .stDataFrame th { background-color: #f2f2f2; font-weight: bold; }
                            .stDataFrame td button { padding: 5px 10px; font-size: 14px; }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        cols = st.columns([1, 4, 2, 2, 4, 2])
                        headers = ["Position", "Team", "Match VPs", "Total VPs", "Competitor", ""]
                        for col, header in zip(cols, headers):
                            with col:
                                st.markdown(f"<div style='font-weight: bold;'>{header}</div>", unsafe_allow_html=True)
                        
                        for idx, row in df.iterrows():
                            team = row["Team"]
                            cols = st.columns([1, 4, 2, 2, 4, 2])
                            values = [
                                str(row["Position"]),
                                row["Team"],
                                row["Match VPs"],
                                row["Total VPs"],
                                row["Competitor"],
                                ""
                            ]
                            for i, (col, value) in enumerate(zip(cols, values)):
                                with col:
                                    if i == 5:
                                        if st.button("View Games", key=f"view_games_{team}_{current_match}_{idx}"):
                                            st.session_state.viewed_team = team
                                            st.session_state.viewed_competitor = row["Competitor"]
                                            st.session_state.viewed_match = current_match
                                            st.session_state.viewed_match_VPs = row["Match VPs"]
                                            st.session_state.viewing_games = True
                                            st.rerun()
                                    else:
                                        style = highlight_selected_team(team) if i == 1 else ''
                                        st.markdown(f"<div style='{style}'>{value}</div>", unsafe_allow_html=True)
                
                # Refresh button in main GUI
                if st.button("Refresh Data"):
                    st.session_state.all_games_data = []
                    st.session_state.cache_timestamp = None
                    st.session_state.viewed_team = None
                    st.session_state.viewed_match = None
                    st.session_state.viewing_games = False
                    st.session_state.data_loaded = False
                    st.rerun()

if __name__ == "__main__":
    app()