import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from streamlit_extras.metric_cards import style_metric_cards

# Set page config for a wider layout
st.set_page_config(layout="wide", page_title="Quiz Analytics Dashboard")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-right: 24px;
        padding-left: 24px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Load and prepare data
@st.cache_data
def load_data():
    correct_answers = pd.read_excel('Correct_Answers.xlsx')
    ques_ans = pd.read_excel('Que_Ans.xlsx')
    voter = pd.read_excel('Voter.xlsx')
    
    # Convert date columns to datetime
    ques_ans['que_created_at'] = pd.to_datetime(ques_ans['que_created_at'], format='%d/%m/%Y %I:%M %p')
    voter['voting_time'] = pd.to_datetime(voter['voting_time'], format='%d/%m/%Y %I:%M %p')
    
    return correct_answers, ques_ans, voter

# 1. Top N most active followers/voters
def top_n_most_active_voters(voter_df, n=10):
    voter_counts = voter_df.groupby('voter_name').size().reset_index(name='vote_count')
    return voter_counts.nlargest(n, 'vote_count')

# 2. Top N early birds
def top_n_early_birds(voter_df, n=10):
    # Get first response time for each user per question
    first_responses = voter_df.groupby(['question_text', 'voter_name'])['voting_time'].min().reset_index()
    # Calculate response time rank for each question
    first_responses['rank'] = first_responses.groupby('question_text')['voting_time'].rank()
    # st.write(first_responses)
    # Get average rank for each user
    # avg_ranks = first_responses.groupby('voter_name')['rank'].mean().reset_index()
    # return avg_ranks.nsmallest(n, 'rank')

    # Filter to keep only the first responders (rank == 1)
    first_responders = first_responses[first_responses['rank'] == 1]
    # Count how many times each voter is the first responder
    first_count = first_responders.groupby('voter_name').size().reset_index(name='first_count')
    # Return
    return first_count.nlargest(n, 'first_count')


# 3. Top N questions with more incorrect answers
def top_n_incorrect_questions(voter_df, correct_answers_df, n=10):
    # Ensure correct_answers_df has unique question-text rows
    answers_df = correct_answers_df.groupby('que_text')['ans_text'].apply(set).reset_index()

    voting_df = voter_df.groupby(['question_text', 'voter_name'])['choice'].apply(set).reset_index()

    # Merge with correct answers to get the correct answers
    merged_df = pd.merge(voting_df, answers_df, left_on='question_text', right_on='que_text')

    merged_df['is_incorrect'] = merged_df.apply(lambda x: x['choice'] != x['ans_text'], axis=1)

    # st.write(merged_df)

    # Aggregate incorrect vote count and total vote count
    question_stats = merged_df.groupby('question_text').agg(
        incorrect_votes = ('is_incorrect', 'sum'),
        total_votes = ('choice', 'size')
    ).reset_index()

    # Calculate incorrect ratio and select top N questions
    question_stats['incorrect_ratio'] = question_stats['incorrect_votes'] / question_stats['total_votes']
    return question_stats.nlargest(n, 'incorrect_ratio')

# 4. Top N easy questions
def top_n_easy_questions(voter_df, correct_answers_df, n=10):
    # Ensure correct_answers_df has unique question-text rows
    answers_df = correct_answers_df.groupby('que_text')['ans_text'].apply(set).reset_index()

    voting_df = voter_df.groupby(['question_text', 'voter_name'])['choice'].apply(set).reset_index()

    # Merge with correct answers to get the correct answers
    merged_df = pd.merge(voting_df, answers_df, left_on='question_text', right_on='que_text')

    merged_df['is_correct'] = merged_df.apply(lambda x: x['choice'] == x['ans_text'], axis=1)

    # st.write(merged_df)

    # Aggregate correct vote count and total vote count
    question_stats = merged_df.groupby('question_text').agg(
        correct_votes = ('is_correct', 'sum'),
        total_votes = ('choice', 'size')
    ).reset_index()

    # Calculate correct ratio and select top N questions
    question_stats['correct_ratio'] = question_stats['correct_votes'] / question_stats['total_votes']
    return question_stats.nlargest(n, 'correct_ratio')

# 5. Top N least active followers/voters
def top_n_least_active_voters(voter_df, n=10):
    voter_counts = voter_df.groupby('voter_name').size().reset_index(name='vote_count')
    return voter_counts.nsmallest(n, 'vote_count')

# 6. Top N voters who haven't participated since long
def top_n_inactive_voters(voter_df, n=10):
    last_vote = voter_df.groupby('voter_name')['voting_time'].max().reset_index()
    last_vote['days_since_last_vote'] = (datetime.now() - last_vote['voting_time']).dt.days
    return last_vote.nlargest(n, 'days_since_last_vote')

# 7. Top N good performers (depending on who answered correct answers the most) 
def top_n_good_performers(voter_df, correct_answers_df, n=10):
    # Ensure correct_answers_df has unique question-text rows
    answers_df = correct_answers_df.groupby('que_text')['ans_text'].apply(set).reset_index()
    
    voting_df = voter_df.groupby(['question_text', 'voter_name'])['choice'].apply(set).reset_index()

    # Merge with correct answers to get the correct answers
    merged_df = pd.merge(voting_df, answers_df, left_on='question_text', right_on='que_text')

    # Calculate correct votes by checking if each answer is in the correct answer set
    merged_df['is_correct'] = merged_df.apply(lambda x: x['choice'] == x['ans_text'], axis=1)

    # st.write(merged_df)

    # Aggregate correct vote count and total vote count
    voter_stats = merged_df.groupby('voter_name').agg(
        correct_votes = ('is_correct', 'sum'),
        total_votes = ('choice', 'size')
    ).reset_index()

    # st.write(voter_stats)

    # Calculate correct ratio and select top N voters
    voter_stats['correct_ratio'] = voter_stats['correct_votes'] / voter_stats['total_votes']
    return voter_stats.nlargest(n, 'correct_ratio')

# 8. Top N difficult questions (least votes)
def top_n_difficult_questions(voter_df, n=10):
    question_votes = voter_df.groupby('question_text')['voter_name'].nunique().reset_index(name='votes')
    # st.write(question_votes)
    return question_votes.nsmallest(n, 'votes')

# 9. Top N fast responded questions
def top_n_fast_responded_questions(voter_df, ques_ans_df, n=10):
    question_response = pd.merge(
        voter_df,
        ques_ans_df[['que_text', 'que_created_at']].drop_duplicates(),
        left_on='question_text',
        right_on='que_text'
    )
    # st.write(question_response)

    question_response = question_response.groupby('question_text').agg(
        first_response_time = ('voting_time', 'min'),
        que_created_at = ('que_created_at', 'min')
    ).reset_index()

    # Calculate the response time in minutes
    question_response['response_time_minutes'] = (
        (question_response['first_response_time'] - question_response['que_created_at']).dt.total_seconds() / 60
    )

    # st.write(question_response)

    # Return the top N questions with the smallest response times
    return question_response.nsmallest(n, 'response_time_minutes')

# 10. Top N slowest responded questions
def top_n_slow_responded_questions(voter_df, ques_ans_df, n=10):
    question_response = pd.merge(
        voter_df,
        ques_ans_df[['que_text', 'que_created_at']].drop_duplicates(),
        left_on='question_text',
        right_on='que_text'
    )
    # st.write(question_response)

    question_response = question_response.groupby('question_text').agg(
        first_response_time = ('voting_time', 'min'),
        que_created_at = ('que_created_at', 'min')
    ).reset_index()

    # Calculate the response time in minutes
    question_response['response_time_minutes'] = (
        (question_response['first_response_time'] - question_response['que_created_at']).dt.total_seconds() / 60
    )

    # st.write(question_response)

    # Return the top N questions with the smallest response times
    return question_response.nlargest(n, 'response_time_minutes')

def create_participation_trend(voter_df):
    daily_participation = voter_df.groupby(voter_df['voting_time'].dt.date).size().reset_index()
    daily_participation.columns = ['date', 'count']
    
    fig = px.line(daily_participation, x='date', y='count',
                  title='Daily Participation Trend',
                  labels={'count': 'Number of Votes', 'date': 'Date'})
    return fig

# Calculate summary metrics
def get_summary_metrics(voter_df, correct_answers_df):
    total_participants = voter_df['voter_name'].nunique()
    total_votes = len(voter_df)
    total_questions = voter_df['question_text'].nunique()
    
    # Calculate accuracy
    answers_df = correct_answers_df.groupby('que_text')['ans_text'].apply(set).reset_index()
    voting_df = voter_df.groupby(['question_text', 'voter_name'])['choice'].apply(set).reset_index()
    merged_df = pd.merge(voting_df, answers_df, left_on='question_text', right_on='que_text')
    merged_df['is_correct'] = merged_df.apply(lambda x: x['choice'] == x['ans_text'], axis=1)
    accuracy = (merged_df['is_correct'].sum() / len(merged_df)) * 100
    
    return {
        'Total Participants': total_participants,
        'Total Votes': total_votes,
        'Total Questions': total_questions,
        'Overall Accuracy': f"{accuracy:.1f}%"
    }

def get_hourly_activity(voter_df):
    """Analyze activity by hour of day"""
    voter_df['hour'] = voter_df['voting_time'].dt.hour
    hourly_activity = voter_df.groupby('hour').size().reset_index(name='count')
    return hourly_activity

def get_weekday_activity(voter_df):
    """Analyze activity by day of week"""
    voter_df['weekday'] = voter_df['voting_time'].dt.day_name()
    weekday_activity = voter_df.groupby('weekday').size().reset_index(name='count')
    # Sort by day of week
    weekday_order = list(calendar.day_name)
    weekday_activity['weekday'] = pd.Categorical(
        weekday_activity['weekday'], categories=weekday_order, ordered=True
    )
    return weekday_activity.sort_values('weekday')

# Main dashboard
def main():
    st.title("📊 Quiz Participation Analytics Dashboard")
    
    # Load data
    correct_answers, ques_ans, voter = load_data()

    # Color theme for plots
    color_theme = px.colors.sequential.Viridis
    
    # Sidebar controls
    with st.sidebar:
        st.title("⚙️ Dashboard Settings")
        n = st.slider("Select Top N", 1, 50, 20)
    
    # Summary metrics in cards
    metrics = get_summary_metrics(voter, correct_answers)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Participants", metrics['Total Participants'])
    with col2:
        st.metric("📝 Total Votes", metrics['Total Votes'])
    with col3:
        st.metric("❓ Total Questions", metrics['Total Questions'])
    with col4:
        st.metric("✅ Overall Accuracy", metrics['Overall Accuracy'])
    style_metric_cards()
    
    # Create tabs with icons
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Participation Trends",
        "👥 Voter Analysis",
        "📝 Question Analysis",
        "🎯 Performance Metrics",
        "⏱️ Response Times",
    ])
    
    with tab1:
        st.header("Participation Trends")

        # Participation Growth
        st.subheader("Daily Activity")
        daily_participation = create_participation_trend(voter)
        st.plotly_chart(daily_participation, use_container_width=True, key='daily_participation')

        st.subheader("Activity Pattern")
        # Two-column layout
        col1, col2 = st.columns(2)
        
        with col1:

            hourly_activity = get_hourly_activity(voter)
            fig_hourly = px.line(hourly_activity, x='hour', y='count', title="Activity by Hour of Day",
                                labels={'count': 'Number of Votes', 'hour': 'Hour of the Day'})
            st.plotly_chart(fig_hourly, use_container_width=True, key='hourly_activity')

        with col2:

            weekday_activity = get_weekday_activity(voter)
            fig_weekday = px.bar(weekday_activity, x='weekday', y='count', title="Activity by Day of Week",
                                labels={'count': 'Number of Votes', 'weekday': 'Day of the Week'},
                                color='count', color_continuous_scale=color_theme)
            st.plotly_chart(fig_weekday, use_container_width=True, key='weekday_activity')

    with tab2:
        st.header("Voter Analysis")
        
        # Two-column layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Most Active Voters
            st.subheader("Most Active Voters")
            active_voters = top_n_most_active_voters(voter, n)
            fig1 = px.bar(active_voters, x='voter_name', y='vote_count',
                         title=f"Top {n} Most Active Voters",
                         labels={'vote_count': 'Number of Votes', 'voter_name': 'Voter Name'},
                         color='vote_count',
                         color_continuous_scale=color_theme)
            st.plotly_chart(fig1, use_container_width=True, key='active_voters')

            # Early Birds
            st.subheader("Early Birds")
            early_birds = top_n_early_birds(voter, n)
            fig2 = px.bar(early_birds, x='voter_name', y='first_count',
                            title=f"Top {n} Early Birds",
                            labels={'first_count': 'Number of First Responses', 'voter_name': 'Voter Name'},
                            color='first_count',
                            color_continuous_scale=color_theme)
            st.plotly_chart(fig2, use_container_width=True, key='early_birds')

        with col2:
            # Least Active Voters
            st.subheader("Least Active Voters")
            inactive_voters = top_n_least_active_voters(voter, n)
            fig3 = px.bar(inactive_voters, x='voter_name', y='vote_count',
                            title=f"Top {n} Least Active Voters",
                            labels={'vote_count': 'Number of Votes', 'voter_name': 'Voter Name'},
                            color='vote_count',
                            color_continuous_scale=color_theme)
            st.plotly_chart(fig3, use_container_width=True, key='inactive_voters')

            # Inactive Users
            st.subheader("Inactive Users")
            inactive_voters = top_n_inactive_voters(voter, n)
            fig4 = px.bar(inactive_voters, x='voter_name', y='days_since_last_vote',
                            title=f"Top {n} Inactive Users",
                            labels={'days_since_last_vote': 'Days Since Last Vote', 'voter_name': 'Voter Name'},
                            color='days_since_last_vote',
                            color_continuous_scale=color_theme)
            st.plotly_chart(fig4, use_container_width=True, key='inactive_users')

    
    with tab3:

        st.header("Question Analysis")
        
        # Incorrect Questions
        incorrect_qs = top_n_incorrect_questions(voter, correct_answers, n)
        fig5 = px.bar(incorrect_qs, x='question_text', y='incorrect_ratio',
                        title=f"Questions with Highest Incorrect Answer Ratio",
                        color='incorrect_ratio',
                        color_continuous_scale=color_theme,
                        labels={'incorrect_ratio': 'Incorrect Answer Ratio', 'question_text': 'Question Text'},
                        height=600)
        st.plotly_chart(fig5, use_container_width=True, key='incorrect_questions')

        # Easy Questions
        easy_qs = top_n_easy_questions(voter, correct_answers, n)
        fig6 = px.bar(easy_qs, x='question_text', y='correct_ratio',
                        title=f"Most Easy Questions",
                        color='correct_ratio',
                        color_continuous_scale=color_theme,
                        labels={'correct_ratio': 'Correct Answer Ratio', 'question_text': 'Question Text'},
                        height=600)
        st.plotly_chart(fig6, use_container_width=True, key='easy_questions')
    
        # Difficult Questions
        difficult_qs = top_n_difficult_questions(voter, n)
        fig6 = px.bar(difficult_qs, x='question_text', y='votes',
                        title=f"Most Challenging Questions",
                        labels={'votes': 'Number of Votes', 'question_text': 'Question Text'},
                        color='votes',
                        color_continuous_scale=color_theme,
                        height=600)
        st.plotly_chart(fig6, use_container_width=True, key='difficult_questions')
    
    with tab4:
        st.header("Performance Analysis")
        
        # Top Performers
        st.subheader("Top Performers")
        performers = top_n_good_performers(voter, correct_answers, n)
        fig5 = px.bar(performers, x='voter_name', y='correct_ratio',
                        title="Performance by Correct Answer Ratio",
                        labels={'correct_ratio': 'Correct Answer Ratio', 'voter_name': 'Voter Name'},
                        color='correct_ratio',
                        color_continuous_scale=color_theme)
        st.plotly_chart(fig5, use_container_width=True, key='top_performers')
    
    with tab5:
        st.header("Response Time Analysis")
        
        # Fast Responses
        st.subheader("Quick Responses")
        fast_qs = top_n_fast_responded_questions(voter, ques_ans, n)
        fig7 = px.bar(fast_qs, x='question_text', y='response_time_minutes',
                    title="Fastest Responded Questions",
                    labels={'response_time_minutes': 'Response Time (Minutes)', 'question_text': 'Question Text'},
                    color='response_time_minutes',
                    color_continuous_scale=color_theme,
                    height=600)
        st.plotly_chart(fig7, use_container_width=True, key='fast_responses')

        # Slow Responses
        st.subheader("Slow Responses")
        slow_qs = top_n_slow_responded_questions(voter, ques_ans, n)
        fig8 = px.bar(slow_qs, x='question_text', y='response_time_minutes',
                        title="Slowest Responded Questions",
                        labels={'response_time_minutes': 'Response Time (Minutes)', 'question_text': 'Question Text'},
                        color='response_time_minutes',
                        color_continuous_scale=color_theme,
                        height=600)
        st.plotly_chart(fig8, use_container_width=True, key='slow_responses')

if __name__ == "__main__":
    main()