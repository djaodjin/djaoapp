/** Functions used for display of localized dates and numbers.
 */

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


function humanizeTimeDelta(at_time, ends_at) {
    var self = this;
    var cutOff = ends_at ? moment(ends_at, DATE_FORMAT) : moment();
    var dateTime = moment(at_time);
    if( dateTime <= cutOff ) {
        var timeAgoTemplate = (self.$labels && self.$labels.timeAgoTemplate) ?
            self.$labels.timeAgoTemplate : "%(timedelta)s ago";
        return timeAgoTemplate.replace("%(timedelta)s",
            moment.duration(cutOff.diff(dateTime)).humanize());
    }
    var timeLeftTemplate = (self.$labels && self.$labels.timeLeftTemplate) ?
        self.$labels.timeLeftTemplate : "%(timedelta)s ago";
    return timeLeftTemplate.replace("%(timedelta)s",
        moment.duration(dateTime.diff(cutOff)).humanize());
};
