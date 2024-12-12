import streamlit as st
import requests
import pandas as pd

# Configurações da API do JIRA
JIRA_URL = "https://omotor.atlassian.net/rest/api/3/search"
EMAIL = "rafael.lima@omotor.com.br"
API_KEY = "ATATT3xFfGF0eoudllQ-7pyhZQenzM_mlDoyngwek5GwnfSk2xMDdyETSLW3UF7GkvHwN7j03Ck88UsuX_aPJ1XfhOa3MIftPtXVzlmUxwSmlYzURk2qRyxoHGm80U14YW3a001crqkvfG6usOvC645Cvrtn91d8kEfFdOrGwu_KlEKDT9kcLi8=0410D171"

# Função para buscar dados da API com paginação
def get_issues(jql):
    max_results = 1000  # Máximo permitido pela API
    start_at = 0
    issues = []
    while True:
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        response = requests.get(JIRA_URL, auth=(EMAIL, API_KEY), params=params)
        data = response.json()
        
        # Adiciona os issues retornados
        issues.extend(data.get("issues", []))
        
        # Verifica se há mais páginas
        if start_at + max_results >= data.get("total", 0):  # Parar quando atingir o total
            break
        
        # Incrementa o startAt para a próxima página
        start_at += max_results
    return issues

# Função para mapear tipos de atividade
def map_activity_type(value):
    # Se o valor for um dicionário, converte para string
    if isinstance(value, dict):
        value = value.get("value", "Outro")  # Usa o campo "value", se existir
    elif isinstance(value, list):
        value = ", ".join([str(v) for v in value])  # Concatena itens da lista
    elif not isinstance(value, str):  # Converte outros tipos para string
        value = str(value)
    
    # Mapeia valores conhecidos
    mapping = {
        "Projeto": "Projeto",
        "Demanda": "Demanda",
        "Sustentação": "Sustentação",
        "POC": "POC"
    }
    return mapping.get(value, "Outro")

# Consulta no JIRA - buscando apenas chamados concluídos nos últimos 45 dias
jql = 'project=JET AND status = "Concluído" AND resolved >= -45d ORDER BY resolved DESC'
issues = get_issues(jql)

# Organizando os dados
df = pd.DataFrame([{
    "Key": issue["key"],
    "Summary": issue["fields"]["summary"],
    "Assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else "Unassigned",
    "Type": issue["fields"]["issuetype"]["name"],
    "Activity Type": map_activity_type(issue["fields"].get("customfield_10217", "Outro")),  # Mapeia tipos conhecidos
    "Parent": issue["fields"]["parent"]["fields"]["summary"] if "parent" in issue["fields"] else "Sem Parent",  # Agora exibe o nome (summary) do Parent
    "Hours Worked": round(issue["fields"].get("customfield_10184") or 0, 2),  # Garante valor numérico antes do arredondamento
    "Created": pd.to_datetime(issue["fields"]["created"]),
    "Resolved": pd.to_datetime(issue["fields"].get("resolutiondate")),  # Data de conclusão
    "Status": issue["fields"]["status"]["name"]
} for issue in issues])

# Filtrar os últimos 45 dias (já feito na JQL, mas mantido para consistência)
filtered_df = df[df["Resolved"] >= (pd.Timestamp.now(tz="America/Sao_Paulo") - pd.DateOffset(days=45))]

# 1. Tabela: Total de Horas por Tipo de Atividade
activity_hours = filtered_df.groupby("Activity Type")["Hours Worked"].sum().reset_index()
activity_hours["Hours Worked"] = activity_hours["Hours Worked"].round(2)  # Ajuste de 2 casas decimais

# 2. Tabela: Horas Trabalhadas por Tipo
issue_type_hours = filtered_df.groupby("Type")["Hours Worked"].sum().reset_index()
issue_type_hours["Hours Worked"] = issue_type_hours["Hours Worked"].round(2)  # Ajuste de 2 casas decimais

# 3. Tabela com Total de Horas por Responsável
responsible_summary = (
    filtered_df.groupby("Assignee")["Hours Worked"]
    .sum()
    .reset_index()
    .rename(columns={"Hours Worked": "Total Hours"})
)
responsible_summary["Total Hours"] = responsible_summary["Total Hours"].round(2)  # Ajuste de 2 casas decimais
activities_by_assignee = (
    filtered_df.groupby(["Assignee", "Type"])["Hours Worked"]
    .sum()
    .unstack(fill_value=0)
)
activities_by_assignee["Total Hours"] = responsible_summary.set_index("Assignee")["Total Hours"]

# 4. Tabela: Total de Horas por Parent
parent_hours = filtered_df.groupby("Parent")["Hours Worked"].sum().reset_index()
parent_hours["Hours Worked"] = parent_hours["Hours Worked"].round(2)  # Ajuste de 2 casas decimais

# 5. Tabela: Cruzamento de Horas por Parent e Tipo de Atividade
parent_activity_hours = (
    filtered_df.groupby(["Parent", "Activity Type"])["Hours Worked"]
    .sum()
    .unstack(fill_value=0)
)
parent_activity_hours = parent_activity_hours.round(2)  # Ajuste de 2 casas decimais

# Dashboard
st.title("Dashboard de Issues - Projeto JET (Chamados Concluídos nos Últimos 45 Dias)")

st.header("Horas por Tipo de Atividade")
st.write("Tabela: Total de Horas por Tipo de Atividade")
st.table(activity_hours)

st.header("Horas Trabalhadas por Tipo")
st.write("Tabela com Total de Horas por Tipo:")
st.table(issue_type_hours)

st.header("Resumo por Responsável")
st.write("Tabela com Total de Horas por Responsável:")
st.table(activities_by_assignee)

st.header("Horas por Parent")
st.write("Tabela: Total de Horas Trabalhadas por Parent")
st.table(parent_hours)

st.header("Cruzamento de Horas: Parent x Tipo de Atividade")
st.write("Tabela: Total de Horas por Parent e Tipo de Atividade")
st.table(parent_activity_hours)