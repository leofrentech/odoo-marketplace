# -*- coding: utf-8 -*-

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    @api.readonly
    def search(self, domain, *args, **kwargs):
        # Overriding search() drops the @api.model/@api.readonly markers the
        # original carries unless redeclared here - odoo/tools/convert.py's
        # XML <function> tag handler checks the _api_model marker to decide
        # whether to treat the first argument as the domain (correct) or pop
        # it off as record ids to browse() first (wrong). Losing it breaks
        # every XML <function name="search"> call during module loading.
        #
        # Some legacy XML-RPC clients (e.g. Zapier's "Odoo ERP Self Hosted"
        # app) send extra positional arguments the current search()
        # signature doesn't accept, in one of two shapes:
        #   1. An extra leading placeholder int before/instead of the
        #      actual domain, followed by offset/limit/order/context - a
        #      shape that worked without error through Odoo 16 (context
        #      just landed in the count slot search() dropped in Odoo 17,
        #      overflowing the positional arguments and raising TypeError
        #      since).
        #   2. A real domain followed by more positional args than
        #      search() accepts (offset, limit, order - 3 extra max), e.g.
        #      context sent positionally too, without the placeholder int.
        #      This doesn't raise the usual "missing domain" TypeError - it
        #      raises "takes from 2 to 5 positional arguments but N were
        #      given" instead, since the domain itself is already valid.
        # Confirmed against real failing calls of both shapes (plus a
        # third remaining shape of case 1: no real domain at all, just
        # limit/order for what looks like "fetch latest record" polling).
        #
        # Only trigger on one of those two unambiguous markers - domain is
        # literally an int (excluding bool, a legitimate domain value in
        # its own right), or there are more positional args than search()
        # accepts. Anything else, including Odoo's own internal Domain
        # object (not a list/tuple, but a perfectly valid domain), passes
        # straight through untouched - this must never re-run its own
        # logic on a call that already works.
        if type(domain) is not int and len(args) <= 3:
            return super().search(domain, *args, **kwargs)

        orig_domain, orig_args, orig_kwargs = domain, args, kwargs
        leftover = list(args)
        if type(domain) is int:
            domain = []
            for i, arg in enumerate(leftover):
                if isinstance(arg, (list, tuple)):
                    domain = leftover.pop(i)
                    break

        # Classify what's left by type rather than assuming a fixed
        # position - the two real shapes seen so far don't agree on where
        # each value sits, but their types are unambiguous: order is
        # always the string, context the dict, and any remaining plain
        # ints are offset/limit in that order (or just limit, if only one).
        context, order, ints = None, None, []
        for arg in leftover:
            if isinstance(arg, dict):
                context = arg
            elif isinstance(arg, str):
                order = arg
            elif isinstance(arg, int) and not isinstance(arg, bool):
                ints.append(arg)

        offset, limit = 0, None
        if len(ints) == 1:
            limit = ints[0]
        elif len(ints) >= 2:
            offset, limit = ints[0], ints[1]

        # recs, not self: with_context() returns a different instance.
        recs = self.with_context(context) if context else self
        try:
            return super(Base, recs).search(  # noqa: UP008
                domain, offset=offset, limit=limit, order=order, **kwargs
            )
        except TypeError:
            # This only fires for a call that was going to fail anyway - log
            # the exact shape (both original and reinterpreted) so an actual
            # fix can be written for it, instead of guessing again.
            _logger.warning(
                "search() failed on %s after reinterpreting a legacy "
                "call - original domain=%r args=%r kwargs=%r; "
                "reinterpreted as domain=%r offset=%r limit=%r "
                "order=%r context=%r",
                self._name, orig_domain, orig_args, orig_kwargs,
                domain, offset, limit, order, context,
            )
            raise
