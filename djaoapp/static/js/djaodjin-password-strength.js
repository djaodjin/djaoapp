/**
   Functionality related to the decorate password fields in djaodjin-signup.

   These are based on jquery.
 */

/* global jQuery */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports', 'jQuery'], factory);
    } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
        // CommonJS
        factory(exports, require('jQuery'));
    } else {
        // Browser true globals added to `window`.
        factory(root, root.jQuery);
        // If we want to put the exports in a namespace, use the following line
        // instead.
        // factory((root.djResources = {}), root.jQuery);
    }
}(typeof self !== 'undefined' ? self : this, function (exports, jQuery) {

(function($){
    "use strict";

    // Toggle password input field visibility on and off.
    function PasswordVisible(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    PasswordVisible.prototype = {
        init: function(){
            var self = this;
            self.$el.parent().find('.' + self.options.offClass).click(
            function(){
                self.toggle();
            });
        },

        toggle: function() {
            var self = this;
            var elems = self.$el.parent().find('.' + self.options.offClass);
            if( elems.length > 0 ) {
                elems.removeClass(self.options.offClass);
                elems.addClass(self.options.onClass);
                self.el.get(0).type = "text";
            } else {
                elems = self.$el.parent().find('.' + self.options.onClass);
                elems.removeClass(self.options.onClass);
                elems.addClass(self.options.offClass);
                self.el.get(0).type = "password";
            }
        }
    };

    $.fn.passwordVisible = function(options){
        var $el = $(this);
        var opts = $.extend( {}, $.fn.passwordVisible.defaults, options );
        if (!$.data($el, "djpasswordvisible")) {
            $el.data("djpasswordvisible", new PasswordVisible($el, opts));
        }
        return $el;
    };

    $.fn.passwordVisible.defaults = {
        onClass: "fa-eye",
        offClass: "fa-eye-slash",
    };

    // Gives feedback on password strength.
    function PasswordStrength(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    PasswordStrength.prototype = {

        init: function(){
            var self = this;
            self.$el.keyup(function(){
                self.calculateStrength(self.$el.val());
            });
        },

        calculateStrength: function(value){
            var self = this;
            var globalStrength = 0;
            var requirements = {};
            var strengthInfo = {};
            var inBlackList = false;

            $.each(self.options.additions, function(index, element){
                var strength = self[element.tester](value);

                if (element.cond.length > 0){
                    var condition = true;
                    $.each(element.cond, function(idx, cond){
                        if (self[cond](value) > 0){
                            condition = false;
                        }
                    });
                    if (!condition){
                        strength = 0;
                    }
                }
                globalStrength += strength;
            });

            $.each(self.options.deductions, function(index, element){
                var strength = self[element](value);
                globalStrength -= self[element](value);
            });

            $.each(self.options.requirements, function(index, element){
                var strength = self[element.tester](value, self.options.minLengthPassword);
                requirements[element.tester] = strength > 0 ? true : false
                if (element.cond.length > 0){
                    var condition = false;
                    $.each(element.cond, function(idx, cond){
                        if (self[cond](value, self.options.minLengthPassword) > 0){
                            condition = true;
                        }
                    });
                    if (!condition){
                        strength = 0;
                    }
                }
                globalStrength += strength;
            });

            if (self.options.blackList.indexOf(value) > 0){
                globalStrength = 0;
                inBlackList = true;
            }

            if (globalStrength < 0){
                globalStrength = 0;
            }else if (globalStrength > 100){
                globalStrength = 100;
            }

            strengthInfo.score = globalStrength;
            if (globalStrength < 25){
                if (!inBlackList){
                    strengthInfo.readableScore = self.options.infoText.level0;
                }else{
                    strengthInfo.readableScore = self.options.infoText.blacklist;
                }
            }else if (globalStrength >= 25 && globalStrength < 40){
                strengthInfo.readableScore = self.options.infoText.level1;
            }else if (globalStrength >= 40 && globalStrength < 60){
                strengthInfo.readableScore = self.options.infoText.level2;
            }else if (globalStrength >= 60 && globalStrength < 80){
                strengthInfo.readableScore = self.options.infoText.level3;
            }else if (globalStrength >= 80){
                strengthInfo.readableScore = self.options.infoText.level4;
            }

            if (!value){
                strengthInfo.readableScore = self.options.infoText.none;
            }

            var progressClass = "text-danger";
            if (strengthInfo.score >= 40 && strengthInfo.score < 60){
                progressClass = "text-warning";
            }else if (strengthInfo.score >= 60 && strengthInfo.score < 80){
                progressClass = "text-success";
            }else if (strengthInfo.score >= 80){
                progressClass = "text-success";
            }

            var feedbackElement = self.$el.parent().siblings(
                self.options.feedbackElement).last();
            feedbackElement
                .removeClass('text-danger text-warning text-success')
                .addClass(progressClass)
                .text(strengthInfo.readableScore);

            self.options.passwordStrengthCallback(strengthInfo, requirements);
        },

        hasMinLength: function(value, min){
            var strength = 0;
            if (value.length >= min){
                strength = 2;
            }
            return strength;
        },
        hasUppercase: function(value){
            var strength = 0;
            if (/[A-Z]/.test(value)){
                strength = 2;
            }
            return strength;
        },
        hasLowercase: function(value){
            var strength = 0;
            if (/[a-z]/.test(value)){
                strength = 2;
            }
            return strength;
        },
        hasSymbol: function(value){
            var strength = 0;
            if (/[^A-Z0-9]/i.test(value)){
                strength = 2;
            }
            return strength;
        },
        hasNumber: function(value){
            var strength = 0;
            if (/[0-9]/.test(value)){
                strength = 2;
            }
            return strength;
        },
        charactersStrength: function(value){
            var number = value.length;
            var strength = (number * 4);
            return strength;
        },
        uppercasesStrength: function(value){
            var number = value.replace(/[^A-Z]/g, "").length;
            var strength = ((value.length - number) * 2);
            if (number === 0){
                strength = 0;
            }
            return strength;
        },
        lowercasesStrength: function(value){
            var number = value.replace(/[^a-z]/g, "").length;
            var strength = ((value.length - number) * 2);
            if (number === 0){
                strength = 0;
            }
            return strength;
        },
        numbersStrength: function(value){
            var number = value.replace(/[^0-9]/g, "").length;
            var strength = (number * 4);
            return strength;
        },
        symbolsStrength: function(value){
            var number = value.replace(/[0-9a-zA-Z]/g, "").length;
            var strength = (number * 6);
            return strength;
        },
        lettersOnly: function(value){
            var number = value.replace(/[^A-Z]/gi, "").length;
            if (value.length === number){
                return number;
            }else{
                return 0;
            }
        },
        numbersOnly: function(value){
            var number = value.replace(/[^0-9]/g, "").length;
            if (value.length === number){
                return number;
            }else{
                return 0;
            }
        },
        consecutiveLowercases: function(value){
            var number = 0;
            for (var i = 1; i < value.length; i++){
                var re = new RegExp("[a-z]{" + (i + 1) + "}", "");
                if (value.match(re)){
                    number += 1;
                }
            }
            var strength = number * 2;
            return strength;
        },
        consecutiveUppercases: function(value){
            var number = 0;
            for (var i = 1; i < value.length; i++){
                var re = new RegExp("[A-Z]{" + (i + 1) + "}", "");
                if (value.match(re)){
                    number += 1;
                }
            }
            var strength = number * 2;
            return strength;
        },
        consecutiveNumbers: function(value){
            var number = 0;
            for (var i = 1; i < value.length; i++){
                var re = new RegExp("[0-9]{" + (i + 1) + "}", "");
                if (value.match(re)){
                    number += 1;
                }
            }
            var strength = number * 2;
            return strength;
        },
        sequentialLetters: function(value){
            var strength = 0;
            var sequences = [
                "abc", "bcd", "cde", "def",
                "efg", "fgh", "ghi", "hij",
                "ijk", "jkl", "klm", "lmn",
                "mno", "nop", "opq", "pqr",
                "qrs", "rst", "stu", "tuv", "uvw",
                "vwx", "wxy", "xyz", "yza", "zab"];

            $.each(sequences, function(index, element){
                if (value.match(element)){
                    strength += 1;
                }
            });
            return strength * 3;
        },
        sequentialNumbers: function(value){
            var strength = 0;
            var sequences = [
                "123", "234", "345", "456",
                "567", "678", "789", "890",
                "901", "012"];

            $.each(sequences, function(index, element){
                if (value.match(element)){
                    strength += 1;
                }
            });
            return strength * 3;
        },
        duplicates: function(value){
            var strength = 0;
            for (var j = 2; j < value.length; j++){
                for (var i = j; i < value.length; i++){
                    var substring = value.substring(i - j, i).replace(/(?=[() ])/g, "\\");
                    var re = new RegExp(substring, "g");
                    var reReplace = new RegExp(substring);
                    var newValue = value.replace(reReplace, "");
                    if (newValue.match(re)){
                        strength += 1;
                    }
                }
            }
            return strength * 4;
        }
    };

    $.fn.passwordStrength = function(options){
        var $el = $(this);
        var opts = $.extend( {}, $.fn.passwordStrength.defaults, options );
        if (!$.data($el, "djpasswordstrength")) {
            $el.data("djpasswordstrength", new PasswordStrength($el, opts));
        }
        return $el;
    };

    $.fn.passwordStrength.defaults = {
        feedbackElement: '.help-block',
        passwordStrengthCallback: function(strength, requirements){
            return true;
        },
        minLengthPassword: 10,
        additions: [
            {tester: "charactersStrength", cond: []},
            {tester: "uppercasesStrength", cond: []},
            {tester: "lowercasesStrength", cond: [
                "lettersOnly",
                "sequentialLetters"]},
            {tester: "numbersStrength", cond: [
                "numbersOnly",
                "sequentialNumbers"]},
            {tester: "symbolsStrength", cond: []}
        ],
        deductions: [
            "lettersOnly",
            "numbersOnly",
            "consecutiveLowercases",
            "consecutiveUppercases",
            "consecutiveNumbers",
            "sequentialLetters",
            "sequentialNumbers",
            "duplicates"
        ],
        requirements: [
            { tester: "hasMinLength", cond: []},
            { tester: "hasUppercase", cond: ["hasMinLength"]},
            { tester: "hasLowercase", cond: ["hasMinLength"]},
            { tester: "hasSymbol", cond: ["hasMinLength"]},
            { tester: "hasNumber", cond: ["hasMinLength"]}
        ],
        blackList: ["password", "1234", "123456", "12345", "12345678",
            "qwerty", "baseball", "football"],
        infoText: {
            blacklist: "Too common",
            none: "",
            level0: "Very weak",
            level1: "Weak",
            level2: "Good",
            level3: "Strong",
            level4: "Very strong"
        }
    };

    // check a password repeat matches another entry
    function PasswordMatch(element, options){
        var self = this;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    PasswordMatch.prototype = {

        init: function(){
            var self = this;
            var reference = $(self.options.reference).first();
            self.$el.keyup(function(){
                self.checkPasswordConfirmation(reference.val());
            });
            reference.keyup(function(){
                self.checkPasswordConfirmation(reference.val());
            });

        },

        checkPasswordConfirmation: function(value){
            var self = this;
            var feedbackElement = self.$el.parent().siblings(
                self.options.feedbackElement).last();
            if( value && value !== "" && self.$el.val() !== "" ) {
                if( self.$el.val() === value ) {
                    feedbackElement
                        .toggleClass(
                            self.options.checkConfirmationClass.match, true)
                        .toggleClass(
                            self.options.checkConfirmationClass.unmatch, false)
                        .text(self.options.checkConfirmationText.match);
                } else {
                    feedbackElement
                        .toggleClass(
                            self.options.checkConfirmationClass.match, false)
                        .toggleClass(
                            self.options.checkConfirmationClass.unmatch, true)
                        .text(self.options.checkConfirmationText.unmatch);
                }
            } else {
                feedbackElement.text("");
            }
        },
    };

    $.fn.passwordMatch = function(options){
        var $el = $(this);
        var opts = $.extend( {}, $.fn.passwordMatch.defaults, options );
        if (!$.data($el, "djpasswordmatch")) {
            $el.data("djpasswordmatch", new PasswordMatch($el, opts));
        }
        return $el;
    };

    $.fn.passwordMatch.defaults = {
        feedbackElement: '.help-block',
        checkConfirmationClass: {
            match: "text-success",
            unmatch: "text-danger"
        },
        checkConfirmationText: {
            match: "Password confirmed.",
            unmatch: "Password and confirmation do not match."
        },
        reference: "[name='new_password']"
    };

}( jQuery ));

}));
