from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template
from rest_framework.response import Response
from rest_framework.views import APIView
from io import BytesIO
from xhtml2pdf import pisa

from .models import *
from .forms import *
from .serializers import CustomerSerializer
import yfinance as yf

from .utils import render_to_pdf

now = timezone.now()


def home(request):
    return render(request, 'portfolio/home.html',
                  {'portfolio': home})


@login_required
def customer_list(request):
    customer = Customer.objects.filter(created_date__lte=timezone.now())
    return render(request, 'portfolio/customer_list.html',
                  {'customers': customer})


@login_required
def customer_new(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_date = timezone.now()
            customer.save()
            customer = Customer.objects.filter(created_date__lte=timezone.now())
            return render(request, 'portfolio/customer_list.html',
                          {'customers': customer})
    else:
        form = CustomerForm()
    return render(request, 'portfolio/customer_new.html', {'form': form})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        # update
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.updated_date = timezone.now()
            customer.save()
            customer = Customer.objects.filter(created_date__lte=timezone.now())
            return render(request, 'portfolio/customer_list.html',
                          {'customers': customer})
    else:
        # edit
        form = CustomerForm(instance=customer)
    return render(request, 'portfolio/customer_edit.html', {'form': form})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    return redirect('portfolio:customer_list')


@login_required
def stock_list(request):
    stocks = Stock.objects.filter(purchase_date__lte=timezone.now())
    return render(request, 'portfolio/stock_list.html', {'stocks': stocks})


@login_required
def stock_new(request):
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.created_date = timezone.now()
            stock.save()
            stocks = Stock.objects.filter(purchase_date__lte=timezone.now())
            return render(request, 'portfolio/stock_list.html',
                          {'stocks': stocks})
    else:
        form = StockForm()
        # print("Else")
    return render(request, 'portfolio/stock_new.html', {'form': form})


@login_required
def stock_edit(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            stock = form.save()
            # stock.customer = stock.id
            stock.updated_date = timezone.now()
            stock.save()
            stocks = Stock.objects.filter(purchase_date__lte=timezone.now())
            return render(request, 'portfolio/stock_list.html', {'stocks': stocks})
    else:
        # print("else")
        form = StockForm(instance=stock)
    return render(request, 'portfolio/stock_edit.html', {'form': form})


@login_required
def stock_delete(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    stock.delete()
    return redirect('portfolio:stock_list')


@login_required
def investment_list(request):
    investments = Investment.objects.filter(acquired_date__lte=timezone.now())
    return render(request, 'portfolio/investment_list.html', {'investments': investments})


@login_required
def investment_new(request):
    if request.method == "POST":
        form = InvestmentForm(request.POST)
        if form.is_valid():
            investment = form.save(commit=False)
            investment.created_date = timezone.now()
            investment.save()
            investments = Investment.objects.filter(recent_date__lte=timezone.now())
            return render(request, 'portfolio/investment_list.html',
                          {'investments': investments})
    else:
        form = InvestmentForm()
        # print("Else")
    return render(request, 'portfolio/investment_new.html', {'form': form})


@login_required
def investment_edit(request, pk):
    investment = get_object_or_404(Investment, pk=pk)
    if request.method == "POST":
        form = InvestmentForm(request.POST, instance=investment)
        if form.is_valid():
            investment = form.save()
            # investment.customer = investment.id
            investment.updated_date = timezone.now()
            investment.save()
            investments = Investment.objects.filter(recent_date__lte=timezone.now())
            return render(request, 'portfolio/investment_list.html', {'investments': investments})
    else:
        # print("else")
        form = InvestmentForm(instance=investment)
    return render(request, 'portfolio/investment_edit.html', {'form': form})


@login_required
def investment_delete(request, pk):
    investment = get_object_or_404(Investment, pk=pk)
    investment.delete()
    investments = Investment.objects.filter(recent_date__lte=timezone.now())
    return render(request, 'portfolio/investment_list.html', {'investments': investments})


@login_required
def portfolio(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customers = Customer.objects.filter(created_date__lte=timezone.now())
    investments = Investment.objects.filter(customer=pk)
    stocks = Stock.objects.filter(customer=pk)
    sum_recent_value = Investment.objects.filter(customer=pk).aggregate(Sum('recent_value'))
    sum_acquired_value = Investment.objects.filter(customer=pk).aggregate(Sum('acquired_value'))
    # overall_investment_results = sum_recent_value-sum_acquired_value
    # Initialize the value of the stocks
    sum_current_stocks_value = 0
    sum_of_initial_stock_value = 0

    # Loop through each stock and add the value to the total
    for stock in stocks:
        sum_current_stocks_value += stock.current_stock_value()
        sum_of_initial_stock_value += stock.initial_stock_value()

    convert_base_url = 'http://api.currencylayer.com/live?access_key='
    convert_api_key = '12e809555b4b89cd312aa4df691ec5d2'
    convert_currency = '&currencies=EUR'
    convert_format = '&format=1'
    convert_url = convert_base_url + convert_api_key + convert_currency + convert_format
    rates = requests.get(convert_url).json()
    eur_conv_rate = rates["quotes"]["USDEUR"]

    return render(request, 'portfolio/portfolio.html', {'customers': customers,
                                                        'investments': investments,
                                                        'stocks': stocks,
                                                        'sum_acquired_value': sum_acquired_value,
                                                        'sum_recent_value': sum_recent_value,
                                                        'sum_current_stocks_value': sum_current_stocks_value,
                                                        'sum_of_initial_stock_value': sum_of_initial_stock_value,
                                                        'customer': customer,
                                                        'eur_rate': eur_conv_rate, })


def fetch_stock_info(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    symbol = stock.symbol

    data_df = yf.download(symbol, start=now-timedelta(days=30), end=now)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}_StockInfo.csv'.format(symbol)
    data_df.to_csv(path_or_buf=response)
    return response


# List at the end of the views.py
# Lists all customers
class CustomerList(APIView):
    def get(self, request, id=None):
        if id:
            customer = Customer.objects.get(id=id)
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)

        customers_json = Customer.objects.all()
        serializer = CustomerSerializer(customers_json, many=True)
        return Response(serializer.data)




@login_required
def portfolio_pdf(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customers = Customer.objects.filter(created_date__lte=timezone.now())
    investments = Investment.objects.filter(customer=pk)
    stocks = Stock.objects.filter(customer=pk)
    sum_recent_value = Investment.objects.filter(customer=pk).aggregate(Sum('recent_value'))
    sum_acquired_value = Investment.objects.filter(customer=pk).aggregate(Sum('acquired_value'))
    # overall_investment_results = sum_recent_value-sum_acquired_value
    # Initialize the value of the stocks
    sum_current_stocks_value = 0
    sum_of_initial_stock_value = 0

    # Loop through each stock and add the value to the total
    for stock in stocks:
        sum_current_stocks_value += stock.current_stock_value()
        sum_of_initial_stock_value += stock.initial_stock_value()

    template = get_template('portfolio/portfolio_pdf.html')
    context = {'customers': customers,
               'investments': investments,
               'stocks': stocks,
               'sum_acquired_value': sum_acquired_value,
               'sum_recent_value': sum_recent_value,
               'sum_current_stocks_value': sum_current_stocks_value,
               'sum_of_initial_stock_value': sum_of_initial_stock_value,
               }
    html = template.render(context)
    pdf = render_to_pdf('portfolio/portfolio_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = "Customers_%s.pdf" % "portfolio"
        content = "inline; filename='%s'" % filename
        download = request.GET.get("download")
        if download:
            content = "attachment; filename='%s'" % (filename)
        response['Content-Disposition'] = content
        return response
    return HttpResponse("Not found")


@login_required
def mutual_fund_list(request):
    mutualfunds = MutualFund.objects.filter(acquired_date__lte=timezone.now())
    return render(request, 'portfolio/mutual_fund_list.html', {'mutualfunds': mutualfunds})


@login_required
def mutual_fund_new(request):
    if request.method == "POST":
        form = MutualFundForm(request.POST)
        if form.is_valid():
            mutualfund = form.save(commit=False)
            mutualfund.created_date = timezone.now()
            mutualfund.save()
            mutualfunds = MutualFund.objects.filter(acquired_date__lte=timezone.now())
            return render(request, 'portfolio/mutual_fund_list.html',
                          {'mutualfunds': mutualfunds})
    else:
        form = MutualFundForm()
        # print("Else")
    return render(request, 'portfolio/mutual_fund_new.html', {'form': form})


@login_required
def mutual_fund_edit(request, pk):
    mutualfund = get_object_or_404(MutualFund, pk=pk)
    if request.method == "POST":
        form = MutualFundForm(request.POST, instance=mutualfund)
        if form.is_valid():
            mutualfund = form.save()

            mutualfund.updated_date = timezone.now()
            mutualfund.save()
            mutualfunds = MutualFund.objects.filter(acquired_date__lte=timezone.now())
            return render(request, 'portfolio/mutual_fund_list.html', {'mutualfunds': mutualfunds})
    else:
        # print("else")
        form = MutualFundForm(instance=mutualfund)
    return render(request, 'portfolio/mutual_fund_edit.html', {'form': form})


@login_required
def mutual_fund_delete(request, pk):
    mutualfund = get_object_or_404(MutualFund, pk=pk)
    mutualfund.delete()
    mutualfunds = MutualFund.objects.filter(acquired_date__lte=timezone.now())
    return render(request, 'portfolio/mutual_fund_list.html', {'mutualfunds': mutualfunds})
