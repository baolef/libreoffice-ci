# Created by Baole Fang at 8/3/23

import pickle
from imblearn.metrics import classification_report_imbalanced
from sklearn import metrics
from tabulate import tabulate
from dash import Dash, dcc, html, Input, Output
import dash_mantine_components as dmc
import plotly.graph_objects as go


def print_labeled_confusion_matrix(confusion_matrix, labels, is_multilabel=False):
    confusion_matrix_table = confusion_matrix.tolist()

    # Don't show the Not classified row in the table output
    if "__NOT_CLASSIFIED__" in labels and not is_multilabel:
        confusion_matrix_table.pop(labels.index("__NOT_CLASSIFIED__"))

    if not is_multilabel:
        confusion_matrix_table = [confusion_matrix_table]

    for num, table in enumerate(confusion_matrix_table):
        if is_multilabel:
            print(f"label: {labels[num]}")
            table_labels = [0, 1]
        else:
            table_labels = labels

        confusion_matrix_header = []
        for i in range(len(table[0])):
            confusion_matrix_header.append(
                f"{table_labels[i]} (Predicted)"
                if table_labels[i] != "__NOT_CLASSIFIED__"
                else "Not classified"
            )
        for i in range(len(table)):
            table[i].insert(0, f"{table_labels[i]} (Actual)")
        return (
            tabulate(table, headers=confusion_matrix_header, tablefmt="fancy_grid"),
        )


with open("testlabelselectmodel_data_y_pred", "rb") as f:
    x = pickle.load(f)[:, 1].reshape(-1, 80)
with open("testfailuremodel_data_y", "rb") as f:
    y = pickle.load(f)
with open("testoverallmodel_data_y_pred", "rb") as f:
    yy = pickle.load(f)[:, 1]

app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='graph'),
    dmc.NumberInput(
        id='count',
        value=10
    ),
    dmc.Slider(
        id='threshold',
        min=0,
        max=1,
        step=0.01,
        value=0.9,
        precision=2,
        updatemode='drag'
    ),
    dmc.Slider(
        id='overall',
        min=0,
        max=1,
        step=0.01,
        value=0.4,
        precision=2,
        updatemode='drag'
    ),
    html.Div(id='report', style={'whiteSpace': 'pre-wrap'}),
    html.Div(id='matrix', style={'whiteSpace': 'pre-wrap'}),
])


@app.callback(
    [Output('graph', 'figure'),
     Output('report', 'children'),
     Output('matrix', 'children')],
    [Input('threshold', 'value'),
     Input('overall', 'value'),
     Input('count', 'value')],
    prevent_initial_call=True
)
def plot(threshold, overall, count):
    data = (x > threshold).sum(axis=1)
    a = data[y == 0]
    b = data[y == 1]

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=a, name='pass'))
    fig.add_trace(go.Histogram(x=b, name='fail'))
    fig.update_layout(barmode='overlay')

    y_pred = (data >= count) | (yy > overall)
    confusion_matrix = metrics.confusion_matrix(
        y, y_pred, labels=[0, 1]
    )
    report = classification_report_imbalanced(
        y, y_pred, labels=[0, 1]
    )

    return fig, report, print_labeled_confusion_matrix(confusion_matrix, [0, 1])


app.run_server()
