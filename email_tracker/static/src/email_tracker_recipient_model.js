/** @odoo-module **/

import { Record } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";

/** Open tracking of one sent email, for one recipient (email.tracker.recipient). */
export class EmailTrackerRecipient extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").EmailTrackerRecipient>} */
    static records = {};
    /** @returns {import("models").EmailTrackerRecipient} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").EmailTrackerRecipient|import("models").EmailTrackerRecipient[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    /** @type {string} */
    email;
    /** @type {string} */
    recipient_label;
    /** @type {number} */
    open_count;
    /** @type {string} server datetime (UTC) */
    first_open_date;
    /** @type {string} server datetime (UTC) */
    last_open_date;
    message = Record.one("Message", {
        onDelete() {
            this.delete();
        },
    });

    get isOpened() {
        return this.open_count > 0;
    }
    get firstOpenDate() {
        return this.first_open_date ? deserializeDateTime(this.first_open_date) : undefined;
    }
    get lastOpenDate() {
        return this.last_open_date ? deserializeDateTime(this.last_open_date) : undefined;
    }
}

EmailTrackerRecipient.register();
