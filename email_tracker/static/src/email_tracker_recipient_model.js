import { fields, Record } from "@mail/model/export";

/** Open tracking of one sent email, for one recipient (email.tracker.recipient). */
export class EmailTrackerRecipient extends Record {
    static _name = "email.tracker.recipient";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    email;
    /** @type {string} */
    recipient_label;
    /** @type {number} */
    open_count;
    first_open_date = fields.Datetime();
    last_open_date = fields.Datetime();
    mail_message_id = fields.One("mail.message", {
        onDelete() {
            this.delete();
        },
    });

    isOpened() {
        return this.open_count > 0;
    }
}

EmailTrackerRecipient.register();
