def migrate(cr, version):
    """Rename the legacy, non-namespaced settings key to the module namespace."""
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET key = 'email_tracker.open_notification'
         WHERE key = 'mail.open.notification'
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter
                WHERE key = 'email_tracker.open_notification'
           )
        """
    )
