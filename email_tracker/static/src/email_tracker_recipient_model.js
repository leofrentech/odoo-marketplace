import { Record } from "@mail/core/common/record";

/** Open tracking of one sent email, for one recipient (email.tracker.recipient). */
export class EmailTrackerRecipient extends Record {
    static _name = "email.tracker.recipient";
    static id = "id";
    /** @type {Object.<number, import("models").EmailTrackerRecipient>} */
    static records = {};

    /** @type {number} */
    id;
    /** @type {string} */
    email;
    /** @type {string} */
    recipient_label;
    /** @type {number} */
    open_count;
    first_open_date = Record.attr(undefined, { type: "datetime" });
    last_open_date = Record.attr(undefined, { type: "datetime" });
    message = Record.one("Message", {
        onDelete() {
            this.delete();
        },
    });

    get isOpened() {
        return this.open_count > 0;
    }
}

EmailTrackerRecipient.register();
