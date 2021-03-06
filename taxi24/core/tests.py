"""
Tests for core app.
"""
from django.test import TestCase
from django.urls import resolve
from rest_framework import status
from rest_framework.test import APITestCase
from core.models import Driver, Passenger, Trip, Bill
from core.serializers import (DriverSerializer, PassengerSerializer,
    TripSerializer)
from core.services import calculate_haversine_distance
from core.views import DriverViewSet, PassengerViewSet, TripViewSet

class ServicesTestCase(TestCase):
    """
    TestCase for module services.
    """
    def test_calculate_haversine_distance(self):
        """
        Test harvesine distance.
        """
        lat = -6.927071
        lon = -79.868941
        distance = calculate_haversine_distance(lat, lon, lat, lon)
        self.assertEqual(distance, 0)

class ResolveTestCase(TestCase):
    """
    TestCase for resolve views.
    """
    def test_resolve_driver_viewset(self):
        """
        Test resolve driver.
        """
        view = resolve('/drivers/')
        self.assertEqual(view.func.__name__, DriverViewSet.__name__)

    def test_resolve_passenger_viewset(self):
        """
        Test resolve passenger.
        """
        view = resolve('/passengers/')
        self.assertEqual(view.func.__name__, PassengerViewSet.__name__)

    def test_resolve_trip_viewset(self):
        """
        Test resolve trip.
        """
        view = resolve('/trips/')
        self.assertEqual(view.func.__name__, TripViewSet.__name__)

class DriverTestCase(APITestCase):
    """
    TestCases for Driver.
    """
    fixtures = ['core']

    def test_list_all_drivers(self):
        """
        Test list all drivers.
        """
        response = self.client.get('/drivers/')
        drivers = Driver.objects.all()
        serializer = DriverSerializer(drivers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 5)

    def test_list_available_drivers(self):
        """
        Test list only drivers with status AVAILABLE.
        """
        response = self.client.get('/drivers/', {'status': Driver.AVAILABLE})
        drivers = Driver.objects.filter(status=Driver.AVAILABLE)
        serializer = DriverSerializer(drivers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 4)

    def test_list_drivers_in_3km(self):
        """
        Test list only drivers with distance less than 3km.
        """
        lat = -6.862689
        lon = -79.818674
        distance = 3
        response = self.client.get('/drivers/',
            {'lat': lat, 'lon': lon , 'distance': distance})
        drivers = Driver.objects.filter_distance(lat, lon, distance)
        serializer = DriverSerializer(drivers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_one_driver(self):
        """
        Test get one driver.
        """
        driver = Driver.objects.first()
        response = self.client.get(f'/drivers/{driver.id}/')
        serializer = DriverSerializer(driver)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

class PassengerTestCase(APITestCase):
    """
    TestCases for Passenger.
    """
    fixtures = ['core']

    def test_list_all_passengers(self):
        """
        Test list all passengers.
        """
        passengers = Passenger.objects.all()
        response = self.client.get('/passengers/')
        serializer = PassengerSerializer(passengers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 2)

    def test_get_one_passenger(self):
        """
        Test get one passenger.
        """
        passenger = Passenger.objects.first()
        response = self.client.get(f'/passengers/{passenger.id}/')
        serializer = PassengerSerializer(passenger)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_closest_driver_by_passenger(self):
        """
        Test return drivers with distance less than 3km.
        """
        distance = 3
        passenger = Passenger.objects.first()
        response = self.client.get(
            f'/passengers/{passenger.id}/closest_driver/')
        drivers = Driver.objects\
            .filter_distance(passenger.lat, passenger.lon, distance)\
            .filter(status=Driver.AVAILABLE)
        serializer = DriverSerializer(drivers, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

class TripViewSet(APITestCase):
    """
    TestCases for Trip.
    """
    fixtures = ['core']

    def post_trip(self):
        """
        Make request for post and returns response.
        """
        lat = -6.862689
        lon = -79.818674
        params = {
            'source_lat': lat,
            'source_lon': lon,
            'destination_lat': lat,
            'destination_lon': lon,
            'passenger': str(Passenger.objects.first().id),
            'driver': str(Driver.objects.first().id),
        }
        return self.client.post('/trips/', params, format='json')

    def test_create_trip(self):
        """
        Test create new trip.
        """
        response = self.post_trip()
        trip = Trip.objects.latest('created')
        serializer = TripSerializer(trip)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(Driver.objects.first().status, Driver.UNAVAILABLE)

    def test_end_trip(self):
        """
        Test end trip and its actions.
        """
        trip = Trip.objects.first()
        response = self.client.put(f'/trips/{trip.id}/ending/')
        serializer = TripSerializer(trip)
        bill = Bill.objects.latest('created')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('id'), serializer.data.get('id'))
        self.assertEqual(response.data.get('status'), Trip.END)
        self.assertEqual(trip.driver.status, Driver.AVAILABLE)
        self.assertEqual(trip.id, bill.trip_id)
        self.assertEqual(trip.destination_lat, trip.driver.lat)
        self.assertEqual(trip.destination_lon, trip.driver.lon)
        self.assertEqual(trip.destination_lat, trip.passenger.lat)
        self.assertEqual(trip.destination_lon, trip.passenger.lon)

    def test_list_active_trip(self):
        """
        Test list only trips with status ACTIVE.
        """
        response = self.client.get('/trips/', {'status': Trip.ACTIVE})
        trips = Trip.objects.filter(status=Trip.ACTIVE)
        serializer = TripSerializer(trips, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
