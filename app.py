import os
import base64
from io import BytesIO
import pandas as pd # pip install pandas
from sklearn.cluster import KMeans # pip install scikit-learn
import streamlit as st # pip install streamlit
import requests # pip install requests

class Transaction:
    def __init__(self, date, description, amount, category):
        self.date = date
        self.description = description
        self.amount = amount
        self.category = category

class Budget:
    def __init__(self, categories):
        self.categories = categories
        self.expenses = []

    def add_expense(self, transaction):
        self.expenses.append(transaction)

    def get_total_expenditure(self):
        total = 0
        for expense in self.expenses:
            total += expense.amount
        return total

    def get_category_expenditure(self, category):
        total = 0
        for expense in self.expenses:
            if expense.category == category.lower():
                total += expense.amount
        return total

    def get_expense_recommendations(self):
        expenses_dict = [vars(expense) for expense in self.expenses]
        data = pd.DataFrame(expenses_dict)
        if 'date' in data.columns:
            data = data.drop(columns=['date'])
        if 'description' in data.columns:
            data = data.drop(columns=['description'])
        data = pd.get_dummies(data, columns=['category'])
        n_clusters = min(3, len(data))
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(data)
        recommendations = {}
        for i, label in enumerate(kmeans.labels_):
            if label not in recommendations:
                recommendations[label] = []
            recommendations[label].append(self.expenses[i])
        return recommendations

def load_data(file_name):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, file_name)
    if not os.path.exists(file_path):
        return []
    data = pd.read_excel(file_path).to_dict(orient='records')
    return data

def save_data(file_name, data):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, file_name)
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)

def get_table_download_link(df):
    towrite = BytesIO()
    df.to_excel(towrite, index=False)  
    towrite.seek(0)  
    b64 = base64.b64encode(towrite.read()).decode()  
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="expenses.xlsx">Download the expenses file</a>'
    return href

def convert_data_to_text(budget):
    categories_text = f"Categories: {', '.join(budget.categories)}\n"
    expenses_text = "Expenses:\n"
    for expense in budget.expenses:
        expenses_text += f"{expense.date} - {expense.description} - {expense.amount} - {expense.category}\n"
    return categories_text + expenses_text

def main():
    st.set_page_config(page_title="Personal Finance Manager", page_icon=":receipt:")
    st.markdown("<h1 style='text-align: center;'>Personal Finance Manager</h1>", unsafe_allow_html=True)
    st.sidebar.title("Choose an action")
    action = st.sidebar.selectbox("",("add", "recommendations"))
    budget = Budget(["Groceries", "Entertainment", "Utilities", "Investments"])
    transactions = load_data("transactions.xlsx")
    for transaction in transactions:
        budget.add_expense(Transaction(**transaction))
    if action == "add":
        st.write("Total Expenditure: ", budget.get_total_expenditure())
        for category in budget.categories:
            st.write(f"{category} Expenditure: ", budget.get_category_expenditure(category))
        date = st.text_input("Enter date (dd/mm/yyyy): ")
        description = st.text_input("Enter description: ")
        amount = st.number_input("Enter amount: ", value=0.0, step=0.01)
        category = st.selectbox("Choose a category", ("Groceries", "Entertainment", "Utilities", "Investments")).lower()
        if st.button("Add Expense"):
            transaction = Transaction(date, description, amount, category)
            budget.add_expense(transaction)
            transactions.append(transaction.__dict__)
            save_data("transactions.xlsx", transactions)
            st.success("Expense added successfully.")
            df = pd.DataFrame(transactions)
            st.markdown(get_table_download_link(df), unsafe_allow_html=True)

    elif action == "recommendations":
        data_text = convert_data_to_text(budget)

        api_key = "wr-BOVjokTARVmFBKmHcFk7Pt"
        url = 'https://api.webraft.in/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "model": "gpt-4",
            "max_tokens": 200,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful expense management assistant."
                },
                {
                    "role": "user",
                    "content": data_text + "\n\nRecommendations:"
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)

        try:
            response_data = response.json()
            st.write(response_data['choices'][0]['message']['content'])
        except requests.exceptions.JSONDecodeError as e:
            st.write("JSON Decode Error:", e)
            st.write("Response Content:", response.content)
            st.write(response.choices[0].text.strip())

if __name__ == "__main__":
    main()