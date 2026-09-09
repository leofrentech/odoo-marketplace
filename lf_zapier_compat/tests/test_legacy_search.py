# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestLegacySearchCompat(TransactionCase):
    """Covers the two real legacy call shapes seen from Zapier's
    "Odoo ERP Self Hosted" app, plus the guards around them.

    res.country is used instead of res.partner because res.partner
    carries its own _search() override with quirks unrelated to this
    module (e.g. it does not accept a bool domain at all here).
    """

    def test_normal_call_passes_through_unaffected(self):
        Country = self.env['res.country']
        countries = Country.search([('name', '!=', False)], limit=3)
        self.assertLessEqual(len(countries), 3)

    def test_legacy_call_with_domain(self):
        Country = self.env['res.country']
        expected = Country.search(
            [('id', '>', 0)], offset=0, limit=5, order='id')
        legacy = Country.search(
            0, [('id', '>', 0)], 0, 5, 'id', {'lang': 'en_US'})
        self.assertEqual(legacy.ids, expected.ids)

    def test_legacy_call_without_domain(self):
        # Confirmed real-world shape: Zapier polling for the latest
        # record, with no domain at all - just limit/order/context.
        Country = self.env['res.country']
        expected = Country.search([], limit=1, order='id desc')
        legacy = Country.search(0, 0, 1, 'id desc', {'lang': 'en_US'})
        self.assertEqual(legacy.ids, expected.ids)

    def test_bool_domain_is_not_treated_as_legacy_marker(self):
        # type(False) is bool, not int - must never trigger the
        # legacy path. A bool is not a valid domain on this Odoo
        # version (the Domain class that accepts True/False as
        # sentinels only exists on 19.0+): if our guard mistakenly
        # treated it as the legacy int marker, this would succeed
        # with every country instead of raising - it must keep
        # failing exactly like it does without this module installed.
        with self.assertRaises(Exception):
            self.env['res.country'].search(False)

    def test_still_raises_when_reinterpretation_also_fails(self):
        # 'count' was removed from search()'s signature - this shape
        # was always going to fail, legacy or not, and must keep
        # raising rather than being silently swallowed.
        with self.assertRaises(TypeError):
            self.env['res.country'].search(0, count=True)
