/** Functions used for display of localized dates and numbers.
 */

var DATE_FORMAT = 'MMM DD, YYYY';


function humanizeDate(at_time) {
    return moment(at_time).format(DATE_FORMAT);
}


function humanizeNumber(cell, unit, scale) {
    scale = scale || 1;
    var value = cell * scale;

    if( typeof Intl !== 'undefined' &&
        typeof Intl.NumberFormat !== 'undefined') {
        var locale = 'en-US';
        if( navigator.languages && navigator.languages.length > 0 ) {
            locale = navigator.languages[0];
        } else if( navigator.language ) {
            locale = navigator.language;
        } else if( navigator.browserLanguage ) {
            locale = navigator.browserLanguage;
        }
        if( unit ) {
            return (new Intl.NumberFormat(locale, {
                style: 'currency', currency: unit})).format(value);
        }
        return (new Intl.NumberFormat(locale)).format(value);
    }

    // `Intl` is not present. Let's do what we can.
    var precision = 0;
    var thousandsSeparator = ',';
    var decimalSeparator = '.';
    var symbol = '';
    var symbolOnLeft = true;

    if( unit ) {
        // We have a currency unit
        if( unit === "usd" || unit === "cad" ) {
            symbol = "$";
        } else if( unit === "eur" ) {
            symbol = "\u20ac";
        }
        precision = 2;
    }

    var stringified = Math.abs(value).toFixed(precision);
    var decimalPart = precision ? stringified.slice(-1 - precision) : '';
    var integralPart = precision ? stringified.slice(0, -1 - precision)
        : stringified;

    var rem = integralPart.length % 3;
    var head = rem > 0 ? (integralPart.slice(0, rem) + (
        integralPart.length > 3 ? thousandsSeparator : ''))
        : '';
    var sign = value < 0 ? '-' : '';
    var valueFormatted = sign + head + integralPart.slice(rem).replace(
        /(\d{3})(?=\d)/g, '$1' + thousandsSeparator) + decimalPart;

    return symbolOnLeft ?
        symbol + valueFormatted : valueFormatted + symbol;
};


function humanizePeriodHeading(atTime, periodType, tzString) {
    // XXX duplicate of `asPeriodHeading` in djaodjin-saas-vue.js
    var datetime = null;
    if( typeof atTime === 'string' ) {
        datetime = new Date(atTime);
    } else {
        datetime = new Date(atTime.valueOf());
    }
    // `datetime` contains aggregated metrics before
    // (not including) `datetime`.
    datetime = new Date(datetime.valueOf() - 1);
    if( typeof tzString === 'undefined' ) {
        tzString = "UTC";
    }
    // `datetime` is in UTC but the heading must be printed
    // in the provider timezone, and not the local timezone
    // of the browser.
    datetime = datetime.toLocaleString('en-US', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false,
        timeZone: tzString});
    const regx = new RegExp(
        '(?<month>\\d\\d)/(?<day>\\d\\d)/(?<year>\\d\\d\\d\\d), (?<hour>\\d\\d):(?<minute>\\d\\d):(?<second>\\d\\d)');
    const parts = regx.exec(datetime);
    const year = parseInt(parts.groups['year']);
    const monthIndex = parseInt(parts.groups['month']) - 1;
    const day = parseInt(parts.groups['day']);
    const hour = parseInt(parts.groups['hour']);
    const minute = parseInt(parts.groups['minute']);
    const second = parseInt(parts.groups['second']);
    const lang = navigator.language;
    if( periodType == 'yearly' ) {
        return parts.groups['year'] + (
            monthIndex !== 11 ? '*' : '');
    }
    if( periodType == 'monthly' ) {
        const dateTimeFormat = new Intl.DateTimeFormat(lang, {
            year: 'numeric',
            month: 'short'
        });
        return dateTimeFormat.format(
            new Date(year, monthIndex)) + ((hour !== 23 &&
                minute !== 59 && second !== 59)  ? '*' : '');
    }
    if( periodType == 'weekly' ) {
        const dateTimeFormat = new Intl.DateTimeFormat(lang, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            weekday: 'short'
        });
        return dateTimeFormat.format(
            new Date(year, monthIndex, day)) + ((hour !== 23 &&
                minute !== 59 && second !== 59)  ? '*' : '');
    }
    if( periodType == 'daily' ) {
        const dateTimeFormat = new Intl.DateTimeFormat(lang, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            weekday: 'short'
        });
        return dateTimeFormat.format(
            new Date(year, monthIndex, day)) + ((hour !== 23 &&
                minute !== 59 && second !== 59)  ? '*' : '');
    }
    if( periodType == 'hourly' ) {
        const dateTimeFormat = new Intl.DateTimeFormat(lang, {
            year: 'numeric',
            month: 'numeric',
            day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: false,
        });
        return dateTimeFormat.format(
            new Date(year, monthIndex, day, hour)) + ((minute !== 59 &&
                second !== 59)  ? '*' : '');
    }
    return datetime.toISOString();
};


function humanizeTimeDelta(at_time, ends_at) {
    var self = this;
    var cutOff = ends_at ? moment(ends_at) : moment();
    var dateTime = moment(at_time);
    if( dateTime <= cutOff ) {
        var timeAgoTemplate = (self.$labels && self.$labels.timeAgoTemplate) ?
            self.$labels.timeAgoTemplate : "%(timedelta)s ago";
        return timeAgoTemplate.replace("%(timedelta)s",
            moment.duration(cutOff.diff(dateTime)).humanize());
    }
    var timeLeftTemplate = (self.$labels && self.$labels.timeLeftTemplate) ?
        self.$labels.timeLeftTemplate : "%(timedelta)s left";
    return timeLeftTemplate.replace("%(timedelta)s",
        moment.duration(dateTime.diff(cutOff)).humanize());
};
