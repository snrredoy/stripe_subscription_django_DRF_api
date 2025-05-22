from .models import Package, Subscription
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime
from django.http import HttpResponse
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import SubscriptionSerializer, PackageSerializer

# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY

class PackageView(APIView):
    def get(self,request,pk=None):
        if pk:
            package = Package.objects.get(pk=pk)
            serializer = PackageSerializer(package)
            response = {
                "status": status.HTTP_200_OK,
                "success": True,
                "message": "Package retrieved successfully",
                "data": serializer.data
            }
            return Response(response)
        packages = Package.objects.all()
        serializer = PackageSerializer(packages, many=True)
        response = {
            "status": status.HTTP_200_OK,
            "success": True,
            "message": "All packages retrieved successfully",
            "data": serializer.data
        }
        return Response(response)

class SubscriptionView(APIView):
    def get(self, request, package_id=None):
        if package_id:
            subscription = Subscription.objects.get(id=package_id)
            serializer = SubscriptionSerializer(subscription)
            response = {
                "status": status.HTTP_200_OK,
                "success": True,
                "message": "Subscription retrieved successfully",
                "data": serializer.data
            }
            return Response(response)
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        response = {
            "status": status.HTTP_200_OK,
            "success": True,
            "message": "All subscriptions retrieved successfully",
            "data": serializer.data
        }
        return Response(response)


class SubscriptionCreate(APIView):
    def post(self, request, package_id):
        user = request.user
        package = Package.objects.get(id=package_id)

        try:
            customers = stripe.Customer.list(email=user.email)

            if customers.data:
                stripe_customer = customers.data[0]
            else:
                stripe_customer = stripe.Customer.create(
                    email= user.email,
                    name=f'{user.first_name} {user.last_name}'
                )
        except stripe.error.StripeError as e:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'success': False,
                'message': 'Failed to create or retrieve customer.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            current_subscription = Subscription.objects.filter(user=user, is_active=True).first()
            stripe_subscription = None

            if current_subscription:
                stripe_subscription = stripe.Subscription.retrieve(current_subscription.stripe_subscription_id)
        except Subscription.DoesNotExist:
            current_subscription = None

        if stripe_subscription:
            try:
                stripe.Subscription.modify(
                    stripe_subscription.id,
                    items=[{
                        'id': stripe_subscription['items']['data'][0].id,
                        'price': package.stripe_price_id
                    }],
                    proration_behavior='create_prorations',
                )
                update_subscription = stripe.Subscription.retrieve(stripe_subscription.id)
                current_subscription.is_active = False
                current_subscription.save()

                new_subscription = Subscription.objects.create(
                    user=user,
                    package = package,
                    stripe_subscription_id = update_subscription.id,
                    end_date = datetime.fromtimestamp(update_subscription['items']['data'][0]['current_period_end']),
                    is_active = True,
                )
                return Response({
                    'status': status.HTTP_200_OK,
                    'success': True,
                    'message': 'Subscription updated successfully.',
                    'data': SubscriptionSerializer(new_subscription).data
                }, status=status.HTTP_200_OK)
            except stripe.error.StripeError as e:
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'message': 'Failed to update subscription.',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types= ['card'],
                    mode='subscription',
                    line_items=[{'price':package.stripe_price_id, 'quantity': 1}],
                    customer=stripe_customer.id,
                    success_url=settings.STRIPE_SUCCESS_URL,
                    cancel_url=settings.STRIPE_CANCEL_URL,
                    metadata={
                        'package_id': str(package_id),
                        'user_id': str(user.id)
                    },
                    subscription_data={
                        'metadata': {
                            'user_id': str(user.id),
                            'package_id': str(package_id),
                        }
                    }
                )
                return Response({
                    'status': status.HTTP_200_OK,
                    'success': True,
                    'message': 'Checkout session created successfully.',
                    'data': {
                        'url': checkout_session.url,
                        'success_url': settings.STRIPE_SUCCESS_URL,
                        'cancel_url': settings.STRIPE_CANCEL_URL,
                    }
                }, status=status.HTTP_200_OK)
            except stripe.error.StripeError as e:
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'success': False,
                    'message': 'Failed to create checkout session.',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_KEY
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status = 400)
    except ValueError as e:
        return HttpResponse(status=400)
    
    if event['type'] == 'customer.subscription.created':
        data = event['data']['object']
        metadata = data.get('metadata', {})
        user_id = metadata.get('user_id')
        package_id = metadata.get('package_id')
        stripe_subscription_id = data['id']

        user = User.objects.get(id=user_id)
        package = Package.objects.get(id=package_id)

        subscription = Subscription.objects.create(
            user=user,
            package=package,
            stripe_subscription_id=stripe_subscription_id,
            end_date = datetime.fromtimestamp(data['current_period_end']),
            is_active = True,
        )
    elif event['type'] == 'customer.subscription.updated':
        data = event['data']['object']
        metadata = data.get('metadata', {})
        user_id = metadata.get('user_id')
        package_id = metadata.get('package_id')
        stripe_subscription_id = data['id']

        user = User.objects.get(id=user_id)
        package = Package.objects.get(id=package_id)

        Subscription.objects.filter(user=user, package=package).update(
            stripe_subscription_id=stripe_subscription_id,
            end_date = datetime.fromtimestamp(data['current_period_end']),
        )
    return HttpResponse(status=200)

class CancelSubscription(APIView):
    def post(self, request, subscription_id):
        user = request.user
        subscription = Subscription.objects.get(pk=subscription_id, user=user)

        try:
            stripe.Subscription.cancel(subscription.stripe_subscription_id)

            subscription.is_active= False
            subscription.save()
            return Response({
                'status': status.HTTP_200_OK,
                'success': True,
                'message': 'Subscription cancelled successfully.',
            }, status=status.HTTP_200_OK)

        except stripe.error.InvalidRequestError as e:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'success': False,
                'message': 'Failed to cancel subscription.',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.RateLimitError as e:
            return Response({
                'status': status.HTTP_429_TOO_MANY_REQUESTS,
                'success': False,
                'message': 'Failed to cancel subscription.',
                'error': str(e)
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
