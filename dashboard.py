import streamlit as st
import requests
import pandas as pd

# Configurações da API do JIRA
JIRA_URL = "https://omotor.atlassian.net/rest/api/3/search"
EMAIL = "rafael.lima@omotor.com.br"
API_KEY = "ATATT3xFfGF0eoudllQ-7pyhZQenzM_mlDoyngwek5GwnfSk2xMDdyETSLW3UF7GkvHwN7j03Ck88UsuX_aPJ1XfhOa3MIftPtXVzlmUxwSmlYzURk2qRyxoHGm80U14YW3a001crqkvfG6usOvC645Cvrtn91d8kEfFdOrGwu_KlEKDT9kcLi8=0410D171"

# Função para buscar dados da API com paginação
def get_issues(jql):
    max_results = 100  # Máximo permitido por página na API
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
        if start_at + max_results >= data.get("total", 0):
            break
        
        # Incrementa o startAt para a próxima página
        start_at += max_results
    return issues

# Função para mapear tipos de atividade
def map_activity_type(value):
    if isinstance(value, dict):
        value = value.get("value", "Outro")
    elif isinstance(value, list):
        value = ", ".join([str(v) for v in value])
    elif not isinstance(value, str):
        value = str(value)
    
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
    "Assignee": issue["fields"].get("assignee", {}).get("displayName", "Unassigned") if issue["fields"].get("assignee") else "Unassigned",
    "Type": issue["fields"]["issuetype"]["name"],
    "Activity Type": map_activity_type(issue["fields"].get("customfield_10217", "Outro")),
    "Parent": issue["fields"].get("parent", {}).get("fields", {}).get("summary", "Sem Parent"),
    "Hours Worked": round(issue["fields"].get("customfield_10184") or 0, 2),
    "Created": pd.to_datetime(issue["fields"]["created"]),
    "Resolved": pd.to_datetime(issue["fields"].get("resolutiondate")).date() if issue["fields"].get("resolutiondate") else None,
    "Status": issue["fields"]["status"]["name"]
} for issue in issues])

# Filtrar os últimos 45 dias (já feito na JQL, mas mantido para consistência)
filtered_df = df[df["Resolved"] >= (pd.Timestamp.now(tz="America/Sao_Paulo") - pd.DateOffset(days=45)).date()]

# 1. Tabela: Total de Horas por Tipo de Atividade
activity_hours = filtered_df.groupby("Activity Type")["Hours Worked"].sum().reset_index()
activity_hours["Hours Worked"] = activity_hours["Hours Worked"].round(2)

# 2. Tabela: Horas Trabalhadas por Tipo
issue_type_hours = filtered_df.groupby("Type")["Hours Worked"].sum().reset_index()
issue_type_hours["Hours Worked"] = issue_type_hours["Hours Worked"].round(2)

# 3. Tabela com Total de Horas por Responsável
responsible_summary = (
    filtered_df.groupby("Assignee")["Hours Worked"]
    .sum()
    .reset_index()
    .rename(columns={"Hours Worked": "Total Hours"})
)
responsible_summary["Total Hours"] = responsible_summary["Total Hours"].round(2)
activities_by_assignee = (
    filtered_df.groupby(["Assignee", "Type"])["Hours Worked"]
    .sum()
    .unstack(fill_value=0)
)
activities_by_assignee["Total Hours"] = responsible_summary.set_index("Assignee")["Total Hours"]

# 4. Tabela: Total de Horas por Parent
parent_hours = filtered_df.groupby("Parent")["Hours Worked"].sum().reset_index()
parent_hours["Hours Worked"] = parent_hours["Hours Worked"].round(2)

# 5. Tabela: Cruzamento de Horas por Parent e Tipo de Atividade
parent_activity_hours = (
    filtered_df.groupby(["Parent", "Activity Type"])["Hours Worked"]
    .sum()
    .unstack(fill_value=0)
)
parent_activity_hours = parent_activity_hours.round(2)

# 6. Tabela: Detalhamento Completo
detailed_table = filtered_df[["Key", "Summary", "Resolved", "Activity Type", "Type", "Parent", "Assignee", "Hours Worked"]]

# Função para gerar CSV
def convert_df_to_csv(dataframe):
    return dataframe.to_csv(index=False).encode('utf-8')

# Dashboard
st.title("Controle de Produtividade e Horas Time OMOTOR (Concluídos nos Últimos 45 Dias)")

st.header("Tipo de Atividade")
st.write("Total de Horas Consumidas por Tipo de Atividade")
st.dataframe(activity_hours, use_container_width=True)

st.header("Issue Type")
st.write("Horas Consumidas por Issue Type")
st.dataframe(issue_type_hours, use_container_width=True)

st.header("Responsável")
st.write("Horas Consumidas Conforme Responsável Pela Solução")
st.dataframe(activities_by_assignee, use_container_width=True)

st.header("Chamado Pai / Projeto")
st.write("Contagem de Horas Por Projeto")
st.dataframe(parent_hours, use_container_width=True)

st.header("Cruzamento de Horas: Projeto x Tipo de Atividade")
st.write("Horas Consumidas Por Projeto x Tipo de Atividade")
st.dataframe(parent_activity_hours, use_container_width=True)

st.header("Chamados Concluídos")
st.write("Tabela com Todos Chamados Resolvidos no Período")
st.dataframe(detailed_table, use_container_width=True, height=400)
