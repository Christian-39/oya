from django.urls import path
from .views import add_contribution, contributions_list, my_contributions, expenses_list, add_expense, income_list, \
    add_income, income_receipt, contribution_receipt, donation_list

urlpatterns = [
    path('contributions/add/', add_contribution, name='add_contribution'),
    path('contributions/', contributions_list, name='contributions_list'),
    path('my-contributions/', my_contributions, name='my_contributions'),
    path('expenses/add/', add_expense, name='add_expense'),
    path('expenses/', expenses_list, name='expenses_list'),
    path('income/', income_list, name='income_list'),
    path('income/add/', add_income, name='add_income'),
    path('income/receipt/<int:income_id>/', income_receipt, name='income_receipt'),
    path('contribution/receipt/<int:contribution_id>/', contribution_receipt, name='contribution_receipt'),
    path('donation/', donation_list, name='donation_list'),

]
