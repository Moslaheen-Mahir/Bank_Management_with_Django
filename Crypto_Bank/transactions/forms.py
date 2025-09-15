
from django import forms
from .models import Transactions

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transactions
        fields = ['amount', 'transaction_type']
        
    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        print("Fields after init:", self.fields)
        self.fields['transaction_type'].disabled = True
        self.fields['transaction_type'].widget = forms.HiddenInput()
        
    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save(commit=commit)

class DepositForm(TransactionForm):
    def clean_amount(self):
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount')
        if amount < min_deposit_amount:
            raise forms.ValidationError(f'You need to deposit at least {min_deposit_amount}$')
        return amount

class WithdrawForm(TransactionForm):
    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance
        amount = self.cleaned_data.get('amount')
        
        if amount < min_withdraw_amount:
            raise forms.ValidationError(f'You can withdraw at least {min_withdraw_amount}$')
        if amount > max_withdraw_amount:
            raise forms.ValidationError(f'You can withdraw at most {max_withdraw_amount}$')
        if amount > balance:
            raise forms.ValidationError(
                f'You have {balance}$ in your account. You cannot withdraw more than your balance'
            )
        return amount

class LoanRequestForm(TransactionForm, forms.ModelForm):
    # class Meta:
    #     model = Transactions
    #     fields = ['amount', 'transaction_type']
    # def __init__(self, *args, **kwargs):
    #     # Ensure account is passed
    #     self.account = kwargs.pop('account', None)
    #     super().__init__(*args, **kwargs)

    #     # Hide the transaction_type field
    #     self.fields['transaction_type'].widget = forms.HiddenInput()

    #     # Optional: add placeholder and styling to amount
    #     self.fields['amount'].widget.attrs.update({
    #         'placeholder': 'Enter loan amount',
    #         'class': 'w-full px-4 py-3 bg-white rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500'
    #     })

    # def save(self, commit=True):
    #     # Link the transaction to the user account
    #     self.instance.account = self.account
    #     # self.instance.balance_after_transaction = self.account.balance
    #     return super().save(commit=commit)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return amount
