import pandas as pd
import streamlit as st
import requests
import plotly.express as px

# Configurações da API do JIRA
JIRA_URL = "https://omotor.atlassian.net/rest/api/3/search"
EMAIL = "rafael.lima@omotor.com.br"
API_KEY = "ATATT3xFfGF0eoudllQ-7pyhZQenzM_mlDoyngwek5GwnfSk2xMDdyETSLW3UF7GkvHwN7j03Ck88UsuX_aPJ1XfhOa3MIftPtXVzlmUxwSmlYzURk2qRyxoHGm80U14YW3a001crqkvfG6usOvC645Cvrtn91d8kEfFdOrGwu_KlEKDT9kcLi8=0410D171"

# Lista com nomes dos meses
meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# Função para buscar dados da API com paginação
def get_issues(jql):
    """
    Busca issues na API do JIRA com paginação.

    Args:
        jql (str): A consulta JQL para buscar as issues.

    Returns:
        list: Uma lista de issues.
    """
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
    """
    Mapeia os tipos de atividade.

    Args:
        value (str): O valor do tipo de atividade.

    Returns:
        str: O tipo de atividade mapeado.
    """
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

# --- Configurações da página ---
st.set_page_config(
    page_title="Dashboard de Produtividade",
    page_icon=":bar_chart:",
    layout="wide"
)

# --- Barra Lateral ---

# URL da imagem do logo online
logo_url = "https://omotor.com.br/wp-content/uploads/2022/07/Logo-azul-1024x345.png"

# Exibe o logo na barra lateral
st.sidebar.image(logo_url, use_container_width=True)

# Opções de período com descrições mais claras
periodo = st.sidebar.radio(
    "Selecione o Período",
    [
        "Mês/Ano Específico",
        "Intervalo de Datas"
    ],
    help="Escolha como você deseja filtrar os dados: por um mês/ano específico ou por um intervalo de datas."
)

data_inicio, data_fim = None, None
if periodo == "Mês/Ano Específico":
    ano = st.sidebar.selectbox("Ano", range(2024, pd.Timestamp.now().year + 1), help="Selecione o ano desejado.")
    mes = st.sidebar.selectbox("Mês", meses, help="Selecione o mês desejado.")
    data_inicio = pd.Timestamp(ano, meses.index(mes) + 1, 1)
    data_fim = (data_inicio + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
else:
    data_inicio = st.sidebar.date_input("Data Inicial", pd.Timestamp.now() - pd.DateOffset(days=30), format="DD/MM/YYYY", help="Selecione a data de início do intervalo.")
    data_fim = st.sidebar.date_input("Data Final", pd.Timestamp.now(), format="DD/MM/YYYY", help="Selecione a data de fim do intervalo.")

# --- Corpo principal do dashboard ---
st.title("Dashboard de Produtividade - Time OMOTOR")

# Botão para gerar relatório
gerar_relatorio = st.sidebar.button("Gerar Relatório")

if gerar_relatorio:
    # Consulta no JIRA com base nas datas selecionadas
    jql = f'project=JET AND status = "Concluído" AND resolved >= "{data_inicio.strftime("%Y-%m-%d")}" AND resolved <= "{data_fim.strftime("%Y-%m-%d")}" ORDER BY resolved DESC'
    issues = get_issues(jql)

    # Organizando os dados
    df = pd.DataFrame([{
        "Chave": issue["key"],
        "Resumo": issue["fields"]["summary"],
        "Responsável": issue["fields"].get("assignee", {}).get("displayName", "Não Atribuído") if issue["fields"].get("assignee") else "Não Atribuído",
        "Tipo de Chamado": issue["fields"]["issuetype"]["name"],
        "Tipo de Atividade": map_activity_type(issue["fields"].get("customfield_10217", "Outro")),
        "Projeto Pai": issue["fields"].get("parent", {}).get("fields", {}).get("summary", "Sem Pai"),
        "Horas Trabalhadas": round(issue["fields"].get("customfield_10184") or 0, 2),
        "Criado em": pd.to_datetime(issue["fields"]["created"], utc=True),
        "Concluído em": pd.to_datetime(issue["fields"].get("resolutiondate"), utc=True).tz_localize(None) if issue["fields"].get("resolutiondate") else None,
        "Status": issue["fields"]["status"]["name"]
    } for issue in issues])

    # Verificar se a coluna "Concluído em" está presente
    if "Concluído em" in df.columns:
        # Filtrar os dados com base nas datas selecionadas
        filtered_df = df[(df["Concluído em"] >= pd.Timestamp(data_inicio).tz_localize("UTC").to_numpy()) & (df["Concluído em"] <= pd.Timestamp(data_fim).tz_localize("UTC").to_numpy())]
    else:
        filtered_df = pd.DataFrame()  # Cria um DataFrame vazio se "Concluído em" não existir

    # Verificar se o DataFrame filtrado não está vazio
    if not filtered_df.empty:
        # --- Métricas ---
        st.header("Métricas")
        total_horas = filtered_df["Horas Trabalhadas"].sum()
        total_chamados = len(filtered_df)
        media_horas_chamado = total_horas / total_chamados if total_chamados > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Horas Trabalhadas", f"{total_horas:.2f}h")
        with col2:
            st.metric("Total de Chamados Concluídos", total_chamados)
        with col3:
            st.metric("Média de Horas por Chamado", f"{media_horas_chamado:.2f}h")

        # --- Gráficos ---
        st.header("Visualização Gráfica")

        # Gráfico de pizza com legendas
        fig = px.pie(
            filtered_df.groupby("Tipo de Atividade")["Horas Trabalhadas"].sum().reset_index(),
            values="Horas Trabalhadas",
            names="Tipo de Atividade",
            title="Distribuição de Horas por Tipo de Atividade",
            color_discrete_sequence=px.colors.qualitative.Set3,  # Usa cores diferentes
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")  # Mostra as legendas dentro das fatias
        fig.update_layout(showlegend=True)  # Mostra a legenda do gráfico

        st.plotly_chart(fig, use_container_width=True)

        # --- Tabelas ---
        st.header("Dados Detalhados")
        
        st.subheader("Horas Trabalhadas por Tipo de Atividade")
        st.dataframe(filtered_df.groupby("Tipo de Atividade")["Horas Trabalhadas"].sum().reset_index(), use_container_width=True)

        st.subheader("Horas Trabalhadas por Tipo de Chamado")
        st.dataframe(filtered_df.groupby("Tipo de Chamado")["Horas Trabalhadas"].sum().reset_index(), use_container_width=True)

        st.subheader("Total de Horas Trabalhadas por Responsável")
        responsible_summary = (
            filtered_df.groupby("Responsável")["Horas Trabalhadas"]
            .sum()
            .reset_index()
            .rename(columns={"Horas Trabalhadas": "Total de Horas"})
        )
        responsible_summary["Total de Horas"] = responsible_summary["Total de Horas"].round(2)
        st.dataframe(responsible_summary, use_container_width=True)

        st.subheader("Total de Horas Trabalhadas por Projeto")
        st.dataframe(filtered_df.groupby("Projeto Pai")["Horas Trabalhadas"].sum().reset_index(), use_container_width=True)

        # ---->>> tabela adicionada aqui <<<---
        st.subheader("Total de Horas Trabalhadas - Projeto x Tipo de Atividade")
        parent_activity_hours = (
            filtered_df.groupby(["Projeto Pai", "Tipo de Atividade"])["Horas Trabalhadas"]
            .sum()
            .unstack(fill_value=0)
            .round(2)
        )
        st.dataframe(parent_activity_hours, use_container_width=True)

        st.subheader("Total de Horas Trabalhadas - Responsável x Projeto")
        responsible_parent_hours = (
            filtered_df.groupby(["Responsável", "Projeto Pai"])["Horas Trabalhadas"]
            .sum()
            .unstack(fill_value=0)
        )
        responsible_parent_hours["Total de Horas"] = responsible_summary.set_index("Responsável")["Total de Horas"]
        responsible_parent_hours = responsible_parent_hours.round(2)
        st.dataframe(responsible_parent_hours, use_container_width=True)

        st.subheader("Detalhes dos Chamados Concluídos")
        st.dataframe(filtered_df[["Chave", "Resumo", "Concluído em", "Tipo de Atividade", "Tipo de Chamado", "Projeto Pai", "Responsável", "Horas Trabalhadas"]], use_container_width=True, height=400)

    else:
        st.warning("Nenhum dado encontrado para o período selecionado.")

# Adiciona um reload automático a cada 30 minutos usando JavaScript
reload_interval = 30 * 60 * 1000  # 30 minutos em milissegundos
st.markdown(
    f"""
    <script>
        setTimeout(function(){{
            window.location.reload();
        }}, {reload_interval});
    </script>
    """,
    unsafe_allow_html=True
)
