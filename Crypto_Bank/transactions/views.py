# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from django.db.models import Sum
from datetime import datetime
from transactions.constants import DEPOSIT, WITHDRAWAL, LOAN, LOAN_PAID
from transactions.forms import DepositForm, WithdrawForm, LoanRequestForm
from transactions.models import Transactions
from accounts.models import UserBankAccount

class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transactions
    title = ''
    success_url = reverse_lazy('transactions:transaction_report')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs.update({'account': self.request.user.account})
        except UserBankAccount.DoesNotExist:
            raise ValueError("You must have a bank account to perform transactions.")
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'title': self.title})
        return context

class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'
    
    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial
    
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(update_fields=['balance'])
        
        form.instance.transaction_type = DEPOSIT
        form.instance.balance_after_transaction = account.balance
        
        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        return super().form_valid(form)

class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'
    
    def get_initial(self):
        return {'transaction_type': WITHDRAWAL}
    
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        self.request.user.account.balance -= amount
        self.request.user.account.save(update_fields=['balance'])
        
        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin, CreateView):
    model = Transactions
    form_class = LoanRequestForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transactions:loan_list')  # change to your URL
    title = 'Request For Loan'
    
    def get_initial(self):
        return {'transaction_type': LOAN}
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs.update({'account': self.request.user.account})
        except UserBankAccount.DoesNotExist:
            raise ValueError("You must have a bank account to perform transactions.")
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        print("Form fields:", form.fields)  # DEBUG: should include 'amount' and 'transaction_type'
        return form
    
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transactions.objects.filter(
            account=self.request.user.account, transaction_type=LOAN, loan_approve=True
        ).count()
        
        if current_loan_count >= 3:
            return HttpResponse("You have crossed the loan limits")
        
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        return super().form_valid(form)
    
    def save(self, commit=True):
        if not self.account:
            raise ValueError("No bank account assigned to this transaction.")
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save(commit=commit)


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transactions
    balance = 0
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(account=self.request.user.account)
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transactions.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
            
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'account': self.request.user.account})
        return context

class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transactions, id=loan_id)
        if loan.loan_approve:
            user_account = loan.account
            if loan.amount <= user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approve = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                # return redirect('transactions:loan_list')
            else:
                messages.error(self.request, 'Loan amount is greater than available balance')
            return redirect('transactions:loan_list')

class LoanListView(LoginRequiredMixin, ListView):
    model = Transactions
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans'
    
    def get_queryset(self):
        return Transactions.objects.filter(
            account=self.request.user.account, transaction_type=LOAN
        )