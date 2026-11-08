"""
Análise de Vendas do E-commerce Brasileiro (Olist)
Autor: Márcio Andrade

Etapas:
1. Carregamento dos dados
2. Verificação de qualidade (nulos e duplicados)
3. Tratamento e junção das tabelas
4. Cálculo dos KPIs
5. Geração dos gráficos
6. Atualização automática do README com os resultados
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PASTA_DADOS = Path("dados")
PASTA_GRAFICOS = Path("graficos")
ARQUIVO_README = Path("README.md")
PASTA_GRAFICOS.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (10, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
COR = "#2E86AB"


def formatar_reais(valor):
    """Formata número no padrão brasileiro: R$ 1.234,56"""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def salvar_grafico(nome):
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / nome, dpi=150)
    plt.close()
    print(f"  Gráfico salvo: graficos/{nome}")


# %% 1. Carregamento dos dados
print("1. Carregando os dados...")
pedidos = pd.read_csv(PASTA_DADOS / "olist_orders_dataset.csv")
itens = pd.read_csv(PASTA_DADOS / "olist_order_items_dataset.csv")
clientes = pd.read_csv(PASTA_DADOS / "olist_customers_dataset.csv")
avaliacoes = pd.read_csv(PASTA_DADOS / "olist_order_reviews_dataset.csv")
produtos = pd.read_csv(PASTA_DADOS / "olist_products_dataset.csv")


# %% 2. Verificação de qualidade
print("\n2. Verificando a qualidade dos dados...")
tabelas = {
    "Pedidos": pedidos,
    "Itens": itens,
    "Clientes": clientes,
    "Avaliações": avaliacoes,
    "Produtos": produtos,
}
for nome, tabela in tabelas.items():
    nulos = tabela.isna().sum()
    nulos = nulos[nulos > 0]
    linhas = f"{len(tabela):,}".replace(",", ".")
    print(f"\n  {nome}: {linhas} linhas | {tabela.duplicated().sum()} duplicadas")
    if not nulos.empty:
        print("  Colunas com valores nulos:")
        for coluna, qtd in nulos.items():
            print(f"    {coluna}: {qtd:,}".replace(",", "."))


# %% 3. Tratamento e junção
print("\n3. Tratando e juntando as tabelas...")
colunas_data = [
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
for coluna in colunas_data:
    pedidos[coluna] = pd.to_datetime(pedidos[coluna])

# Considera apenas pedidos entregues e com data de entrega preenchida
entregues = pedidos[pedidos["order_status"] == "delivered"].dropna(
    subset=["order_delivered_customer_date"]
).copy()

entregues["dias_entrega"] = (
    entregues["order_delivered_customer_date"] - entregues["order_purchase_timestamp"]
).dt.days
entregues["no_prazo"] = (
    entregues["order_delivered_customer_date"].dt.normalize()
    <= entregues["order_estimated_delivery_date"]
)
entregues["mes"] = entregues["order_purchase_timestamp"].dt.to_period("M")

# Um pedido pode ter mais de uma avaliação: usa a média por pedido
nota_por_pedido = avaliacoes.groupby("order_id")["review_score"].mean()
entregues["nota"] = entregues["order_id"].map(nota_por_pedido)

base = (
    itens.merge(entregues[["order_id", "customer_id", "mes"]], on="order_id")
    .merge(clientes[["customer_id", "customer_state"]], on="customer_id")
    .merge(produtos[["product_id", "product_category_name"]], on="product_id", how="left")
)
base["product_category_name"] = base["product_category_name"].fillna("sem_categoria")
print(f"  Base final: {len(base):,} itens vendidos em {base['order_id'].nunique():,} pedidos".replace(",", "."))


# %% 4. KPIs
print("\n4. Calculando os KPIs...")
faturamento = base["price"].sum()
total_pedidos = base["order_id"].nunique()
ticket_medio = faturamento / total_pedidos
pct_no_prazo = entregues["no_prazo"].mean() * 100
prazo_medio = entregues["dias_entrega"].mean()
nota_media = entregues["nota"].mean()

kpis = {
    "Faturamento total": formatar_reais(faturamento),
    "Pedidos entregues": f"{total_pedidos:,}".replace(",", "."),
    "Ticket médio": formatar_reais(ticket_medio),
    "Entregas no prazo": f"{pct_no_prazo:.1f}%".replace(".", ","),
    "Prazo médio de entrega": f"{prazo_medio:.1f} dias".replace(".", ","),
    "Nota média de avaliação": f"{nota_media:.2f} / 5".replace(".", ","),
}
for nome, valor in kpis.items():
    print(f"  {nome}: {valor}")


# %% 5. Gráficos
print("\n5. Gerando os gráficos...")

# 5.1 Faturamento mensal
# Os meses das pontas da base têm poucos pedidos, então o período é limitado
faturamento_mensal = base.groupby("mes")["price"].sum()
faturamento_mensal = faturamento_mensal.loc[pd.Period("2017-01"):pd.Period("2018-08")]
plt.plot(faturamento_mensal.index.to_timestamp(), faturamento_mensal.values / 1000,
         marker="o", color=COR)
plt.title("Faturamento mensal (R$ mil)")
plt.ylabel("R$ mil")
salvar_grafico("01_faturamento_mensal.png")

# 5.2 Top 10 categorias
top_categorias = base.groupby("product_category_name")["price"].sum().nlargest(10)
top_categorias.index = top_categorias.index.str.replace("_", " ")
top_categorias.sort_values().div(1000).plot.barh(color=COR)
plt.title("Top 10 categorias por faturamento (R$ mil)")
plt.xlabel("R$ mil")
plt.ylabel("")
salvar_grafico("02_top_categorias.png")

# 5.3 Faturamento por estado
por_estado = base.groupby("customer_state")["price"].sum().nlargest(10)
por_estado.sort_values().div(1000).plot.barh(color=COR)
plt.title("Top 10 estados por faturamento (R$ mil)")
plt.xlabel("R$ mil")
plt.ylabel("")
salvar_grafico("03_faturamento_por_estado.png")

# 5.4 Impacto do atraso na avaliação
nota_por_prazo = entregues.groupby("no_prazo")["nota"].mean()
nota_por_prazo.index = nota_por_prazo.index.map({True: "No prazo", False: "Atrasado"})
barras = plt.bar(nota_por_prazo.index, nota_por_prazo.values, color=["#C0392B", COR])
plt.bar_label(barras, fmt="%.2f")
plt.title("Nota média de avaliação: entregas no prazo x atrasadas")
plt.ylim(0, 5)
salvar_grafico("04_nota_por_prazo.png")


# %% 6. Atualizar o README com os resultados
print("\n6. Atualizando o README...")
estado_lider = por_estado.index[0]
participacao_estado = por_estado.iloc[0] / faturamento * 100
nota_atrasado = nota_por_prazo.get("Atrasado", float("nan"))
nota_prazo = nota_por_prazo.get("No prazo", float("nan"))

bloco = ["| Indicador | Resultado |", "|---|---|"]
bloco += [f"| {nome} | {valor} |" for nome, valor in kpis.items()]
bloco += [
    "",
    "### Principais conclusões",
    "",
    f"- **{top_categorias.index[0].capitalize()}** é a categoria com maior faturamento.",
    f"- **{estado_lider}** concentra {participacao_estado:.1f}% do faturamento total.".replace(".", ",", 1),
    f"- Pedidos entregues com atraso recebem nota média de **{nota_atrasado:.2f}**, "
    f"contra **{nota_prazo:.2f}** dos entregues no prazo".replace(".", ",")
    + (": o cumprimento do prazo é um fator decisivo na satisfação do cliente."
       if nota_prazo - nota_atrasado >= 0.5
       else ", sem diferença relevante entre os dois grupos."),
]

INICIO, FIM = "<!-- RESULTADOS_INICIO -->", "<!-- RESULTADOS_FIM -->"
if ARQUIVO_README.exists():
    readme = ARQUIVO_README.read_text(encoding="utf-8")
    if INICIO in readme and FIM in readme:
        antes = readme.split(INICIO)[0]
        depois = readme.split(FIM)[1]
        novo = f"{antes}{INICIO}\n" + "\n".join(bloco) + f"\n{FIM}{depois}"
        ARQUIVO_README.write_text(novo, encoding="utf-8")
        print("  README atualizado com os KPIs e conclusões.")
    else:
        print("  Marcadores não encontrados no README; nada foi alterado.")

print("\nAnálise concluída!")
