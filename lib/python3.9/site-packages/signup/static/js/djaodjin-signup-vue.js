/** Components running in the browser.
 */

Vue.filter('formatDate', function(value, format) {
  if (value) {
    if(!format){
        format = 'MM/DD/YYYY hh:mm'
    }
    if(!(value instanceof Date)){
        value = String(value);
    }
    return moment(value).format(format)
  }
});

var DATE_FORMAT = 'MMM DD, YYYY';


var userPasswordModalMixin = {
    data: function () {
        return {
            password: '',
            // not the best solution, but no choice if we want
            // to show the error inside a modal
            passwordIncorrect: false
        };
    },
    methods: {
        modalShow: function() {
            var vm = this;
            vm.password = '';
            vm.passwordIncorrect = false;
            if(vm.dialog){
                vm.dialog.modal("show");
            }
        },
        modalHide: function(){
            if(this.dialog){
                this.dialog.modal("hide");
            }
        },
        failCb: function(res){
            var vm = this;
            if(res.status === 403){
                // incorrect password
                vm.passwordIncorrect = true;
            } else {
                vm.modalHide();
                showErrorMessages(res);
            }
        },
    },
    computed: {
        dialog: function(){ // XXX depends on jQuery / bootstrap.js
            var dialog = $(this.modalSelector);
            if(dialog && jQuery().modal){
                return dialog;
            }
        },
    },
}


Vue.component('contact-list', {
    mixins: [
        itemListMixin,
        paginationMixin
    ],
    data: function () {
        return {
            url: this.$urls.api_contacts,
            redirect_url: this.$urls.contacts,
            contact: {
                full_name: "",
                nick_name: "",
                email: ""
            },
        };
    },
    methods: {
        createContact: function() {
            var vm = this;
            vm.reqPost(vm.url, this.contact,
            function(resp) {
                window.location = vm.redirectUrl(resp.slug);
            }, function(resp) {
                showErrorMessages(resp);
            });
        },
        redirectUrl: function(contact) {
            var vm = this;
            return vm.redirect_url + contact + '/';
        }
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('contact-update', {
    mixins: [itemListMixin, paginationMixin],
    data: function () {
        return {
            url: this.$urls.api_activities,
            typeaheadUrl: this.$urls.api_candidates,
            activityText: '',
            itemSelected: {
                slug: ''
            },
            searching: false,
        };
    },
    methods: {
        createActivity: function() {
            var vm = this;
            var data = {
                text: vm.activityText,
                account: vm.itemSelected.slug
            }
            vm.reqPost(vm.url, {
                text: vm.activityText,
                account: vm.itemSelected.slug
            }, function(resp) {
                vm.get();
            }, function(resp){
                showErrorMessages(resp);
            });
        },
        getCandidates: function(query, done) {
            var vm = this;
            vm.searching = true;
            vm.reqGet(vm.typeaheadUrl, {q: query},
            function(resp){
                vm.searching = false;
                done(resp.results)
            });
        },
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('user-update', {
    mixins: [httpRequestMixin],
    data: function () {
        return {
            url: this.$urls.user.api_profile,
            picture_url: this.$urls.user.api_user_picture,
            redirect_url: this.$urls.user.profile_redirect,
            api_activate_url: this.$urls.user.api_activate,
            api_generate_keys_url: this.$urls.user.api_generate_keys,
            formFields: {},
            userModalOpen: false,
            apiModalOpen: false,
            apiKey: gettext("Generating ..."),
            picture: null,
            password: '',
        };
    },
    methods: {
        activate: function() {
            var vm = this;
            vm.reqPost(vm.api_activate_url,
            function(resp) {
                showMessages([interpolate(gettext(
                    "Activation e-mail successfuly sent to %s"),
                    [resp.email])], "info");
            }, function(resp){
                showErrorMessages(resp);
            });
        },
        resetKey: function(){
            this.apiModalOpen = true;
        },
        generateKey: function() {
            var vm = this;
            vm.reqPost(vm.api_generate_keys_url,
                { password: vm.password },
            function(resp) {
                vm.apiKey = resp.secret;
            }, function(resp){
                if(resp.responseJSON && resp.responseJSON.length > 0) {
                    // this most likely tells that the password
                    // is incorrect
                    vm.apiKey = resp.responseJSON[0];
                    return;
                }
                showErrorMessages(resp);
            });
        },
        deleteProfile: function() {
            var vm = this;
            vm.reqDelete(vm.url,
            function() {
                window.location = vm.redirect_url;
            }, function(resp){
                showErrorMessages(resp);
            });
        },
        get: function(){
            var vm = this;
            vm.reqGet(vm.url,
            function(resp) {
                vm.formFields = resp;
            });
        },
        updateProfile: function(){
            var vm = this;
            vm.validateForm();
            var data = {}
            for( var field in vm.formFields ) {
                if( vm.formFields.hasOwnProperty(field) &&
                    vm.formFields[field] ) {
                    data[field] = vm.formFields[field];
                }
            }
            vm.reqPatch(vm.url, data,
            function(resp) {
                // XXX should really be success but then it needs to be changed
                // in Django views as well.
                showMessages([gettext("Profile updated.")], "info");
            }, function(resp){
                showErrorMessages(resp);
            });
            if(vm.imageSelected){
                vm.uploadProfilePicture();
            }
        },
        uploadProfilePicture: function() {
            var vm = this;
            vm.picture.generateBlob(function(blob){
                if(!blob) return;
                var form = new FormData();
                form.append('file', blob, vm.picture.getChosenFile().name);
                vm.reqPostBlob(vm.picture_url, form,
                function(resp) {
                    vm.formFields.picture = resp.location;
                    vm.picture.remove();
                    vm.$forceUpdate();
                    showMessages(["Profile was updated."], "success");
                });
            }, 'image/jpeg');
        },
        validateForm: function(){ // XXX depends on jQuery
            var vm = this;
            var isEmpty = true;
            var fields = $(vm.$el).find('[name]').not(
                '[name="csrfmiddlewaretoken"]');
            for( var fieldIdx = 0; fieldIdx < fields.length; ++fieldIdx ) {
                var fieldName = $(fields[fieldIdx]).attr('name');
                var fieldValue = $(fields[fieldIdx]).val();
                if( vm.formFields[fieldName] !== fieldValue ) {
                    vm.formFields[fieldName] = fieldValue;
                }
                if( vm.formFields[fieldName] ) {
                    // We have at least one piece of information
                    // about the plan already available.
                    isEmpty = false;
                }
            }
            return !isEmpty;
        },
    },
    computed: {
        imageSelected: function(){
            return this.picture && this.picture.hasImage();
        }
    },
    mounted: function(){
        var vm = this;
        if( !vm.validateForm() ) {
            // It seems the form is completely blank. Let's attempt
            // to load the profile from the API then.
            vm.get();
        }
    },
});


Vue.component('user-update-password', {
    mixins: [
        httpRequestMixin,
        userPasswordModalMixin
    ],
    data: function () {
        return {
            url: this.$urls.user.api_password_change,
            modalSelector: '.user-password-modal',
            newPassword: '',
            newPassword2: '',
        };
    },
    methods: {
        modalShowAndValidate: function() {
            var vm = this;
            if(vm.newPassword != vm.newPassword2){
                showMessages([gettext(
                    "Password and confirmation do not match.")], "danger");
                return;
            }
            vm.modalShow();
        },
        updatePassword: function(){
            var vm = this;
            // We are using the view (and not the API) so that the redirect
            // to the profile page is done correctly and a success message
            // shows up.
            vm.reqPut(vm.url, {
                password: vm.password,
                new_password: vm.newPassword,
                new_password2: vm.newPassword2
            }, function(resp) {
                vm.modalHide();
                vm.newPassword = '';
                vm.newPassword2 = '';
                showMessages([gettext("Password was updated.")], "success");
            }, vm.failCb);
        },
        submitPassword: function(){
            var vm = this;
            vm.updatePassword();
        },
    },
});


Vue.component('user-update-pubkey', {
    mixins: [
        httpRequestMixin,
        userPasswordModalMixin
    ],
    data: function () {
        return {
            url: this.$urls.user.api_pubkey,
            modalSelector: '.user-password-modal',
            pubkey: '',
        };
    },
    methods: {
        updatePubkey: function(){
            var vm = this;
            vm.reqPut(vm.url, {
                pubkey: vm.pubkey,
                password: vm.password,
            }, function(resp){
                vm.modalHide();
                showMessages([gettext("Public key was updated.")], "success");
            }, vm.failCb);
        },
        submitPassword: function(){
            var vm = this;
            vm.updatePubkey();
        },
    },
});
