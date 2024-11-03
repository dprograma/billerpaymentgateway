"""
Transaction Views
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination

from amaps.permissions import IsSenderOrReceiverOwner, IsSenderOwner
from transactions.models import Deposit, WalletTransaction, Transaction
from transactions.serializers import DepositSerializer, TransactionSerializer
from transactions.utils import commission_calculation, wallet_transaction
from userservice.models import Donation

# from .models import Transaction


class DepositWallet(APIView):
    def get(self, request, ref=None):
        if ref:
            deposit = Deposit.objects.get(reference=ref)
            serializer = DepositSerializer(deposit)
            return Response({"status": "success", "response": "", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            deposits = Deposit.objects.all()
            serializer = DepositSerializer(deposits, many=True)
            return Response({"status": "success", "response": "", "data": serializer.data}, status=status.HTTP_200_OK)
        

class CombinedTransactionView(APIView):
    def get(self, request, ref=None):
        user = request.user
        paginator = PageNumberPagination()
        paginator.page_size = 1000  # Set the default page size

        search_query = request.GET.get('search', '')  # Get the search query from the request
        if ref:
            try:
                # Search for the transaction in all three tables
                deposit = Deposit.objects.filter(reference=ref).first().order_by('-date')
                wallet_transaction = WalletTransaction.objects.filter(reference=ref).first().order_by('-date')
                withdrawal_transaction = Transaction.objects.filter(reference=ref).first().order_by('-date')
                # donation_transaction = Donation.objects.filter(reference=ref).first().order_by('-date')

                # Return the transaction found
                if deposit:
                    serializer = DepositSerializer(deposit)
                    return Response({"status": "success", "response": "Deposit transaction retrieved successfully", "data": serializer.data}, status=status.HTTP_200_OK)
                elif wallet_transaction:
                    serializer = TransactionSerializer(wallet_transaction) 
                    return Response({"status": "success", "response": "Wallet transaction retrieved successfully", "data": serializer.data}, status=status.HTTP_200_OK)
                elif withdrawal_transaction:
                    serializer = TransactionSerializer(withdrawal_transaction)  
                    return Response({"status": "success", "response": "Withdrawal transaction retrieved successfully", "data": serializer.data}, status=status.HTTP_200_OK)
                else:
                    return Response({"status": "error", "response": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"status": "error", "response": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif user:
            try:
                # Combine all transactions
                deposit_transactions = Deposit.objects.filter(user_id=user.id).order_by('-date')
                wallet_transactions = WalletTransaction.objects.filter(sender_wallet__user_id=user.id).order_by('-date') | WalletTransaction.objects.filter(recipient_wallet__user_id=user.id).order_by('-date')
                withdrawal_transactions = Transaction.objects.filter(user_id=user.id).order_by('-date')
                # donation_transactions = Donation.objects.all().order_by('-date')
                
                # print("deposit transactions: ", list(deposit_transactions.values()))
                # print()
                # print("wallet transactions: ", list(wallet_transactions.values()))
                # print()
                # print("transactions: ", list(withdrawal_transactions.values()))

                # Apply search filter
                if search_query:
                    deposit_transactions = deposit_transactions.filter(Q(reference__icontains=search_query) | Q(amount__icontains=search_query) | Q(date__icontains=search_query) | Q(payment_type__icontains=search_query))
                    wallet_transactions = wallet_transactions.filter(Q(reference__icontains=search_query) | Q(amount__icontains=search_query) | Q(date__icontains=search_query) | Q(payment_type__icontains=search_query))
                    withdrawal_transactions = withdrawal_transactions.filter(Q(reference__icontains=search_query) | Q(amount__icontains=search_query) | Q(date__icontains=search_query) | Q(payment_type__icontains=search_query))
                    # donation_transactions = donation_transactions.filter(Q(reference__icontains=search_query) | Q(amount__icontains=search_query) | Q(date__icontains=search_query) | Q(payment_type__icontains=search_query))

                # Combine all the querysets into one list
                all_transactions = list(deposit_transactions) + list(wallet_transactions) + list(withdrawal_transactions)

                # Paginate the combined list
                paginated_transactions = paginator.paginate_queryset(all_transactions, request)
                
                # Serialize the paginated transactions
                deposit_serializer = DepositSerializer(paginated_transactions, many=True)
                result = paginator.get_paginated_response(deposit_serializer.data)
                print("paginated transactions: ", result.data)
                return paginator.get_paginated_response(deposit_serializer.data)

            except Exception as e:
                return Response({"status": "error", "response": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

       

class AllTransactionView(APIView):
    def get(self, request):
        paginator = PageNumberPagination()
        paginator.page_size = 100000  
        try:
            # Get all transactions
            deposit_transactions = Deposit.objects.all().order_by('-date')
            wallet_transactions = WalletTransaction.objects.all().order_by('-date')
            withdrawal_transactions = Transaction.objects.all().order_by('-date')
            # donation_transactions = Donation.objects.all().order_by('-date')

            # Combine all the querysets into one list
            all_transactions = list(deposit_transactions) + list(wallet_transactions) + list(withdrawal_transactions)
            # Paginate the combined list
            paginated_transactions = paginator.paginate_queryset(all_transactions, request)
            
            # Serialize the paginated transactions
            deposit_serializer = DepositSerializer(paginated_transactions, many=True)
            return paginator.get_paginated_response(deposit_serializer.data)

        except Exception as e:
            return Response({"status": "error", "response": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
'''       
class TransactionList(generics.ListCreateAPIView):
    """
    List existing transaction or add new one (curr. user)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSenderOwner]

    serializer_class = TransactionSerializer

    def get_queryset(self) -> QuerySet[Transaction]:
        """
        Show only transactions where either receiver or sender
        wallet is of user's
        """
        user = self.request.user
        queryset = Transaction.objects.filter(Q(sender__user=user) | Q(receiver__user=user))
        return queryset

    def perform_create(self, serializer: TransactionSerializer) -> None:
        """
        Transfer money between two wallets
        """
        transfer_amount = serializer.validated_data.get(
            "transfer_amount", Transaction.default_transfer_amount
        )
        sender = serializer.validated_data["sender"]
        receiver = serializer.validated_data["receiver"]
        commission = commission_calculation(sender, receiver, transfer_amount)  ####
        serializer.validated_data["commission"] = commission
        try:
            wallet_transaction(sender, receiver, transfer_amount, commission)
            serializer.save(status="PAID")
        except ObjectDoesNotExist:
            raise ValidationError
        except ValidationError:
            serializer.save(status="FAILED")

    def create(self, request, *args, **kwargs):
        """
        Change status to 201 for FAILED and serialized transactions
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class TransactionDetail(generics.RetrieveDestroyAPIView):
    """
    Detail of individual Transaction
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSenderOwner]
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_object(self) -> Transaction:
        """
        Get Transaction or 404 if it doesn't exist
        """
        transaction_id = self.kwargs["id"]
        transaction = generics.get_object_or_404(Transaction, id=transaction_id)
        self.check_object_permissions(self.request, transaction)
        return transaction


class TransactionWalletList(generics.ListAPIView):
    """
    All transactions where wallet was sender or receiver
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSenderOrReceiverOwner]
    serializer_class = TransactionSerializer

    def get_queryset(self) -> QuerySet[Transaction]:
        user = self.request.user
        queryset = Transaction.objects.filter(Q(sender__user=user) | Q(receiver__user=user))
        return queryset
'''

'''

class TransactionCreateView(generics.CreateAPIView):
        """Views for operating ``Transaction`` model.

            * GET (get): list all transactions
        """
        queryset = Transaction.objects.all()
        serializer_class = TransactionSerializer




class TransactionView(APIView):
    """Views for operating ``Transaction`` model.

        * GET (get): list all transactions
        * GET (get_by_wallet): list all transaction of a specific wallet
        * POST: create a transaction
        * DELETE: delete a transaction (if it possible)

        Fields `wallet` and `transaction_type` are required,
        other fields have default values.
    """

    # def get(self, request):
    #     transactions = Transaction.objects.all()
    #     serializer = TransactionSerializer(transactions, many=True)
    #     return Response(serializer.data)

    @staticmethod
    @api_view(['GET', ])
    def get_by_wallet(request, wallet_slug: str):
        if request.method == 'GET':
            wallet = get_object_or_404(Wallet, slug=wallet_slug)
            transactions = Transaction.objects.filter(wallet=wallet)
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

    ###update transaction...
    @transaction_decorators.atomic
    def post(self, request):
        wallet = get_object_or_404(Wallet, name=request.data['wallet'])
        transaction = Transaction(wallet=wallet)
        serializer = TransactionCreateUpdateSerializer(transaction,
                                                       data=request.data)
        if serializer.is_valid():
            transaction = Transaction(**serializer.validated_data)
            transaction.wallet = wallet
            transaction, success = transaction.provide_transaction()
            if success:
                serializer.save()
                return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    
    def delete(self, request, id: int):
        transaction = get_object_or_404(Transaction, id=id)
        try:
            transaction.delete()
        except utils.IntegrityError:
            data = {'details': 'The transaction cannot be deleted.'}
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)
        return Response(status=status.HTTP_200_OK)


 
    def send_fund_wallet(self, request):
        # Get the sender and receiver from the request data
        sender_id = request.data.get('sender')
        receiver_id = request.data.get('receiver')
        amount = request.data.get('amount')

        # Get the sender and receiver Wallet objects
        sender = get_object_or_404(Wallet, id=sender_id)
        receiver = get_object_or_404(Wallet, id=receiver_id)

        # Create a new Transaction object
        transaction = Transaction(sender=sender, receiver=receiver, amount=amount, transaction_type='Withdrawal')
        transaction.save()

        # Subtract the amount from the sender's balance
        sender.balance -= amount
        sender.save()

        # Add the amount to the receiver's balance
        receiver.balance += amount
        receiver.save()

        return Response({'message': 'Transaction successful'})

        
'''
