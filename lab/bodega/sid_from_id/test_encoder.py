"""Test SID encoder."""
from django.db import models
from django.test import TestCase

from .encoder import SidEncoder
from .models import ModelWithSidFromId


class A(ModelWithSidFromId, models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        # Necessary to avoid errors since these ad hoc models are not in
        # real apps.
        app_label = 'sid_from_id_test'


class AA(A):
    name_a = models.CharField(max_length=100)

    class Meta:
        # Necessary to avoid errors since these ad hoc models are not in
        # real apps.
        app_label = 'sid_from_id_test'


class AB(A):
    name_b = models.CharField(max_length=100)

    class Meta:
        # Necessary to avoid errors since these ad hoc models are not in
        # real apps.
        app_label = 'sid_from_id_test'


class B(ModelWithSidFromId, models.Model):
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Necessary to avoid errors since these ad hoc models are not in
        # real apps.
        app_label = 'sid_from_id_test'


class SidEncoderTestCase(TestCase):
    def assert_encoding_results(self, model, pk):
        sidEncoder = SidEncoder(model)
        sid = sidEncoder.encode(pk)
        decoded_sid = sidEncoder.decode(sid)
        self.assertIsInstance(
            sid, str,
            msg='Encoded SID should be a string')
        self.assertIn(
            '-', sid,
            msg='Encoded SID should have hyphen character')
        self.assertEqual(
            pk, decoded_sid,
            msg='Decoding an encoded SID should match the original ID')

    def test_encoding_results(self):
        self.assert_encoding_results(A, 1)
        self.assert_encoding_results(A, 2)
        self.assert_encoding_results(A, 3)
        self.assert_encoding_results(A, 1000)
        self.assert_encoding_results(A, 1000000)
        self.assert_encoding_results(A, 1000000000)

        self.assert_encoding_results(B, 1)
        self.assert_encoding_results(B, 2)
        self.assert_encoding_results(B, 3)
        self.assert_encoding_results(B, 1000)
        self.assert_encoding_results(B, 1000000)
        self.assert_encoding_results(B, 1000000000)

    def assert_decode_value_error(self, model, bad_sid):
        sidEncoder = SidEncoder(model)
        with self.assertRaises(ValueError):
            sidEncoder.decode(bad_sid)

    def test_decode_value_error(self):
        self.assert_decode_value_error(A, '')
        self.assert_decode_value_error(A, 'bad-sid')
        self.assert_decode_value_error(
            A, 'impossible-sid-for-unrecognized-label-_COLO:edge_dynapod')

    def assert_no_conflicts(self, model_pk_pairs):
        sids = [
            SidEncoder(model).encode(pk) for (model, pk) in model_pk_pairs
        ]

        sid_set = set(sids)
        self.assertEqual(
            len(sids), len(sid_set),
            'Encoded SIDs should not conflict with each other')

    def test_no_conflicts(self):
        self.assert_no_conflicts([
            (A, 1),
            (A, 2),
            (A, 3),
            (A, 1000),
            (A, 1000000),
            (A, 1000000000),
            (B, 1),
            (B, 2),
            (B, 3),
            (B, 1000),
            (B, 1000000),
            (B, 1000000000)
        ])

    def assert_subclass_sids(self, model, submodel, pk):
        modelSidEncoder = SidEncoder(model)
        submodelSidEncoder = SidEncoder(submodel)

        modelSid = modelSidEncoder.encode(pk)
        submodelSid = submodelSidEncoder.encode(pk)

        self.assertEqual(
            submodelSid, modelSid,
            'Encoded SIDs in submodels should match that of parent model.')

    def test_subclass_sids(self):
        self.assert_subclass_sids(A, AA, 1)
        self.assert_subclass_sids(A, AA, 2)
        self.assert_subclass_sids(A, AA, 3)
        self.assert_subclass_sids(A, AA, 1000)
        self.assert_subclass_sids(A, AA, 1000000)
        self.assert_subclass_sids(A, AA, 1000000000)

        self.assert_subclass_sids(A, AB, 1)
        self.assert_subclass_sids(A, AB, 2)
        self.assert_subclass_sids(A, AB, 3)
        self.assert_subclass_sids(A, AB, 1000)
        self.assert_subclass_sids(A, AB, 1000000)
        self.assert_subclass_sids(A, AB, 1000000000)
