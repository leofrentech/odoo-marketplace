# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestLegacySearchCompat(TransactionCase):
    """Covers the two real legacy call shapes seen from Zapier's
    "Odoo ERP Self Hosted" app, plus the guards around them.
    """

    def test_normal_call_passes_through_unaffected(self):
        Partner = self.env['res.partner']
        partners = Partner.search([('name', '!=', False)], limit=3)
        self.assertLessEqual(len(partners), 3)

    def test_legacy_call_with_domain(self):
        Partner = self.env['res.partner']
        expected = Partner.search(
            [('id', '>', 0)], offset=0, limit=5, order='id')
        legacy = Partner.search(
            0, [('id', '>', 0)], 0, 5, 'id', {'lang': 'en_US'})
        self.assertEqual(legacy.ids, expected.ids)

    def test_legacy_call_without_domain(self):
        # Confirmed real-world shape: Zapier polling for the latest
        # record, with no domain at all - just limit/order/context.
        Partner = self.env['res.partner']
        expected = Partner.search([], limit=1, order='id desc')
        legacy = Partner.search(0, 0, 1, 'id desc', {'lang': 'en_US'})
        self.assertEqual(legacy.ids, expected.ids)

    def test_bool_domain_is_not_treated_as_legacy_marker(self):
        # type(False) is bool, not int - must never trigger the
        # legacy path. False is a valid domain in its own right
        # (Odoo treats it as "match nothing", unlike [] which means
        # "no filter") and must keep behaving exactly as it does
        # without this module installed - not get coerced to [].
        self.assertEqual(self.env['res.partner'].search(False).ids, [])

    def test_still_raises_when_reinterpretation_also_fails(self):
        # 'count' was removed from search()'s signature - this shape
        # was always going to fail, legacy or not, and must keep
        # raising rather than being silently swallowed.
        with self.assertRaises(TypeError):
            self.env['res.partner'].search(0, count=True)
