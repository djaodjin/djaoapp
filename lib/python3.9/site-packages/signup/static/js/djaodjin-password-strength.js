/* global jQuery: true*/

(function($){
    "use strict";

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

            var progressbar = $(
"<div class=\"progress\" style=\"margin-bottom:0;border-radius:0;height:4px;\">"
+ "<div class=\"progress-bar password-strength\" role=\"progressbar\" aria-valuenow=\"60\" aria-valuemin=\"0\" aria-valuemax=\"100\" style=\"width: 0%;\">"
+ "</div></div><div><small class=\"strength-info text-muted\"></small></div>");
            progressbar.insertAfter(self.$el);

            self.$el.keyup(function(){
                self.calculateStrength($(this).val());
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

            var progressClass = "progress-bar-danger";
            if (strengthInfo.score >= 40 && strengthInfo.score < 60){
                progressClass = "progress-bar-warning";
            }else if (strengthInfo.score >= 60 && strengthInfo.score < 80){
                progressClass = "progress-bar-success";
            }else if (strengthInfo.score >= 80){
                progressClass = "progress-bar-success";
            }
            self.$el.parent().find(".password-strength").removeClass(
                "progress-bar-danger progress-bar-warning progress-bar-success").addClass(progressClass).attr("style", "width:" + strengthInfo.score + "%");
            self.$el.parent().find(".strength-info").text(strengthInfo.readableScore);

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
        var opts = $.extend( {}, $.fn.passwordStrength.defaults, options );
        if (!$.data($(this), "djpasswordstrength")) {
            $(this).data("djpasswordstrength",
                new PasswordStrength($(this), opts));
        }
    };

    $.fn.passwordStrength.defaults = {
        passwordStrengthCallback: function(strength, requirements){
            return true;
        },
        minLengthPassword: 8,
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
            blacklist: gettext("Too common"),
            none: "",
            level0: gettext("Very weak"),
            level1: gettext("Weak"),
            level2: gettext("Good"),
            level3: gettext("Strong"),
            level4: gettext("Very strong")
        }
    };

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
            $(self.options.checkConfirmationTemplate).insertAfter(self.$el);

            self.$el.keyup(function(){
                self.checkPasswordConfirmation($(self.options.reference).val());
            });
            $(self.options.reference).keyup(function(){
                self.checkPasswordConfirmation($(self.options.reference).val());
            });

        },

        checkPasswordConfirmation: function(value){
            var self = this;
            if( value && value !== "" && self.$el.val() !== "" ) {
                if( self.$el.val() === value ) {
                    self.$el.parent().find('.password-match')
                        .toggleClass(
                            self.options.checkConfirmationClass.match, true)
                        .toggleClass(
                            self.options.checkConfirmationClass.unmatch, false)
                        .text(self.options.checkConfirmationText.match);
                } else {
                    self.$el.parent().find('.password-match')
                        .toggleClass(
                            self.options.checkConfirmationClass.match, false)
                        .toggleClass(
                            self.options.checkConfirmationClass.unmatch, true)
                        .text(self.options.checkConfirmationText.unmatch);
                }
            } else {
                self.$el.parent().find('.password-match').text("");
            }
        },
    };

    $.fn.passwordMatch = function(options){
        var opts = $.extend( {}, $.fn.passwordMatch.defaults, options );
        if (!$.data($(this), "djpasswordmatch")) {
            $(this).data("djpasswordmatch", new PasswordMatch($(this), opts));
        }
    };

    $.fn.passwordMatch.defaults = {
        checkConfirmationClass: {
            match: "text-success",
            unmatch: "text-danger"
        },
        checkConfirmationText: {
            match: gettext("Password confirmed."),
            unmatch: gettext("Password and confirmation do not match.")
        },
        checkConfirmationTemplate: "<div class=\"password-match\"></div>"
    };

    $(document).ready(function(){
        $("[name='new_password']").passwordStrength();
        $("[name='new_password2']").passwordMatch({
            reference: $("[name='new_password']").first()});
    });

}(jQuery));
