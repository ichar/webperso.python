// ***************************************
// PROVISIO DIALOGS: /provision.dialogs.js
// ---------------------------------------
// Version: 1.0
// Date: 25-06-2019

// ===========================
// Dialog windows declarations
// ===========================

var $ProvisionServiceDialog = {
    container    : null,
    form         : null,

    // ========================
    // Provision Uploader Class
    // ========================

    IsDebug : 0, IsTrace : 0, IsLog : 0,

    id           : null,
    action       : '',
    default_form : 'filter',

    init: function(id) {
        this.id = id;

        if (!is_empty(this.id))
            this.container = $("#"+this.id+"-confirm-container");
        
        this.form = $("#"+(this.id || this.default_form)+"-form");
    },

    upload: function() {
        this.init('provisionuploader');

        //alert(this.form.width());

        $("#filename", this.form).prop('placeholder', keywords['Choose a File']).val('');
        $("#uploadButton", this.form).val('');
        $("#command", this.form).val('admin:upload');
        
        $BaseDialog.open(this.id);
    },

    download: function() {
        this.init();

        confirm_action = 'admin:download';
        $ConfirmDialog.open(
            keywords['Command:Provision Orders downloading'] + '<br>' +
            keywords['Data will be filtered accordingly'] + 
            '', 
            500);
    },

    deleteOrders: function() {
        this.init();

        confirm_action = 'admin:delete-orders';
        $ConfirmDialog.open(
            keywords['Command:Provision Orders deleting'] + '<br>' +
            keywords['Data will be filtered accordingly'] + 
            '', 
            500);
    },

    clearHistory: function() {
        this.init();

        confirm_action = 'admin:clear-history';
        $ConfirmDialog.open(
            keywords['Command:Provision Orders history clearing'] + '<br>' +
            keywords['Data will be filtered accordingly'] + 
            '', 
            500);
    },

    sendApproval: function() {
        this.action = null;

        confirm_action = 'admin:send-approval';
        $ConfirmDialog.open(
            keywords['Command:Provision Orders send approval request'] +
            '', 
            500);
    },

    sendReviewNotification: function() {
        this.action = null;

        confirm_action = 'admin:send-review-notification';
        $ConfirmDialog.open(
            keywords['Command:Provision Review notification request'] + '<br>' +
            keywords['Data will be filtered accordingly'] + 
            '', 
            600);
    },

    sendOrderNotification: function() {
        this.action = null;

        confirm_action = 'admin:send-order-notification';
        $ConfirmDialog.open(
            keywords['Command:Provision Order notification request'] +
            '', 
            500);
    },

    lived: function(action) {
        var callback = null;

        switch (confirm_action) {
            case 'admin:send-approval':
                this.action = '844';
                params = {};
                callback = approval_sent;
                break;
            case 'admin:send-review-notification':
                this.action = '851';
                params = {};
                callback = approval_sent;
                break;
            case 'admin:send-order-notification':
                this.action = '852';
                params = {};
                callback = approval_sent;
                break;
        }

        if (!is_empty(this.action))
            $Handle(this.action, function(x) { callback(x); }, params);
    },

    confirmed: function(command) {
        $("#command", this.form).val(command || confirm_action);

        $BaseDialog.run(this.default_form);
    }
};

var $ProvisionImageLoader = {
    container    : null,

    // ========================
    // Provision Selector Class
    // ========================

    IsDebug : 0, IsTrace : 0, IsLog : 0,

    action  : null,
    command : null,
    ob      : null,

    init: function() {},

    add_document: function(ob, command) {
        this.action = 'upload';
        this.command = command;
        this.ob = ob;

        var order_id = SelectedGetItem(LINE, 'id');
        var box = $("#uploadDocument");

        //alert(box.attr('id'));

        var data = new FormData();

        data.append('action', this.action);
        data.append('file', box[0].files[0]);
        data.append('order_id', order_id);
        data.append('filename', $("#document_filename").val());
        data.append('note', $("#document_value").val());

        $web_uploader(this.action, data, function(x) { 
            $PageLoader.handle_document('847', $ProvisionImageLoader.ob, $ProvisionImageLoader.command, x); 
        });
    }
};

var $ProvisionSelectorDialog = {
    base         : $BaseScreenDialog,

    // ========================
    // Provision Selector Class
    // ========================

    IsDebug : 0, IsTrace : 0, IsLog : 0,

    command      : null,
    id           : null,
    oid          : null,
    data         : null,
    columns      : null,
    props        : null,

    // Mode of screen available
    mode         : 'client',
    // Flag to lock screen
    with_lock    : 0,

    is_error     : false,

    init: function(ob, id, title, css) {
        this.id = id;

        this.base.init(ob, this.id, this);

        if (this.IsLog)
            console.log('$ProvisionSelectorDialog.init:', this.id, this.base.form.width(), this.base.form.height());

        if (!is_null(this.base.box) && !is_empty(css))
            this.base.box.removeClass('createorder').removeClass('updateorder').addClass(css);

        if (!is_empty(title))
            this.base.container.dialog("option", "title", title);
    },

    term: function() {
        this.base.term();
    },

    reset: function() {
        this.base.reset(false);
    },

    lock_scroll: function() {
        if (!this.with_lock)
            return;

        this.base.lock_scroll();
    },

    unlock_scroll: function() {
        if (!this.with_lock)
            return;

        this.base.unlock_scroll();
    },

    setDefaultSize: function() {
        var offset = {'H' : [210, 0, 0], 'W' : [65, 0, 0], 'init' : [0, 760-$_width('client')]};

        this.base.setDefaultSize(offset);

        $BaseDialog.open(this.id);
    },

    checked: function(x) {
        var errors = x['errors'];

        if (!is_empty(errors)) {
            var msg = errors.join('<br>');
            $ShowError(msg, true, true, false);
            this.is_error = true;
            return;
        }

        if (this.command == 'updateorder')
            this.enabled();

        $BaseDialog.confirmed();
    },

    enabled: function() {
        var self = $ProvisionSelectorDialog;

        if (this.IsDebug)
            alert('enabled');

        this.columns.forEach(function(name, index) {
            var control_id = self.id+'_'+name;
            var prop = self.props[name];
            var prop_type = prop['type'];
            var prop_disabled = prop['disabled'];
            var ob = $("#"+control_id, self.form);

            if (prop_disabled) {
                ob.prop("disabled", false);

                if (prop_type == 1) {
                    var new_ob = $("#new_"+control_id, self.form);
                    new_ob.prop("disabled", false);
                }
            }
        });
    },

    refreshed: function(x) {
        var self = $ProvisionSelectorDialog;
        
        this.data = x['data'];
        this.columns = x['columns'];
        this.props = x['props'];

        this.columns.forEach(function(name, index) {
            var control_id = self.id+'_'+name;
            var value = self.data[name];
            var prop = self.props[name];
            var prop_type = prop['type'];
            var prop_disabled = prop['disabled'];
            var ob = $("#"+control_id, self.form);

            if (self.IsLog)
                console.log(name, value, prop, is_exist(ob));

            if (prop_type == 2)
                ob.prop("selectedIndex", value);
            else if (prop_type == 1) {
                var sob = $("#new_"+control_id, self.form);
                if (!is_null(sob))
                    sob.val('');
                ob.val(value);
            }
            else
                ob.val(value);

            ob.prop("disabled", prop_disabled);

            if (prop_type == 1) {
                var new_ob = $("#new_"+control_id, self.form);
                new_ob.prop("disabled", prop_disabled);
            }
        });

        this.open(self.command);
    },

    open: function(command) {
        $("#command", this.base.form).val('admin:'+command);

        if (this.IsDebug)        
            alert('open:'+command);

        var cacheid = this.base.cacheid;

        var html = this.base.box.html().replace('order-form', cacheid); 

        this.base.load(html);

        this.setDefaultSize();
    },

    create: function() {
        this.command = 'createorder';

        var action = '843';
        var params = {'command':this.command};

        no_window_scroll = true;

        this.init(null, 'order', keywords['Title:Create Provision order form'], this.command);

        $web_logging(action, function(x) { $ProvisionSelectorDialog.refreshed(x); }, params);
    },

    update: function() {
        this.command = 'updateorder';

        this.oid = $LineSelector.get_id();

        if (is_empty(this.oid))
            return;

        var action = '843';
        var params = {'command':this.command, 'id':this.oid};

        this.init(null, 'order', keywords['Title:Update Provision order form'], this.command);

        $web_logging(action, function(x) { $ProvisionSelectorDialog.refreshed(x); }, params);
    },

    delete: function() {
        this.command = 'deleteorder';

        no_window_scroll = true;

        this.init(null, 'order');

        this.oid = $LineSelector.get_id();

        if (is_empty(this.oid))
            return;

        confirm_action = 'admin:deleteorder';
        $ConfirmDialog.open(
            keywords['Command:Provision Order removing'] + 
            '<br><div class="removescenario">'+keywords['ID order']+':&nbsp;<span>'+this.oid+'</span></div>', 
            500);
    },

    clone: function() {
        this.command = 'cloneorder';

        this.oid = $LineSelector.get_id();

        if (is_empty(this.oid))
            return;

        var action = '843';
        var params = {'command':this.command, 'id':this.oid};

        no_window_scroll = true;

        this.init(null, 'order', keywords['Title:Clone Provision order form'], this.command);

        $web_logging(action, function(x) { $ProvisionSelectorDialog.refreshed(x); }, params);
    },

    validate: function() {
        var self = $ProvisionSelectorDialog;

        var action = '845';
        var params = {'command':this.command};

        this.columns.forEach(function(name, index) {
            var control_id = self.id+'_'+name;
            var ob = $("#"+control_id, self.form);

            if (!is_null(ob))
                params[control_id] = ob.val();

            var prop = self.props[name];
            var prop_type = prop['type'];

            if (prop_type == 1) {
                var new_id = 'new_'+control_id;
                var new_ob = $("#"+new_id, self.form);

                if (!is_null(new_ob))
                    params[new_id] = new_ob.val();
            }
        });

        $web_logging(action, function(x) { $ProvisionSelectorDialog.checked(x); }, params);
    },

    onClose: function() {
        this.term();
    },

    confirmed: function() {
        $("#order_id", this.base.container).val(this.oid);
        $("#command", this.base.form).val(confirm_action);

        $BaseDialog.run(this.id);
    },

    cancel: function() {
        $BaseDialog.cancel();
    }
};

var $ProvisionReviewDialog = {
    container    : null,
    box          : null,
    ob           : null,

    // ======================
    // Provision Review Class
    // ======================

    IsDebug : 0, IsTrace : 0, IsLog : 0,

    action       : '',
    command      : null,
    id           : null,
    mode         : null,
    params       : null,

    init: function(id) {
        this.container = $("#"+this.id+"-confirm-container");
    },

    term: function() {
        this.container = null;
        this.box = null;
        this.ob = null;
        this.action = '';
        this.command = null;
        this.id = null;
        this.params = null;

        selected_menu_action = '';
    },

    setDefaultSize: function(mode) {
        this.box = $("#"+this.id+"-box");

        $("#order-request").html(keywords[
            mode == 'paid' ? 'Assign pay date for the current order' : 
                             'You have to assign due date for confirmation of the order'
        ]);
        $("#review-caption").html(keywords[
            mode == 'paid' ? 'Order pay date assigment see in the application documentation' : 
                             'Review confirmation rules see in the application documentation.'
        ]);
        $(".duedate", this.box).html(keywords[
            mode == 'review' ? 'Review due date' : 'Order pay date'
        ]);
    },

    open: function(ob, mode) {
        if (this.IsTrace)
            alert('$ProvisionReviewDialog.open, mode:'+mode);

        this.ob = ob;

        switch (mode) {
            case 'review':
                this.command = 'REVIEW_CONFIRM';
                this.action = '834';
                this.id = 'review';
                break;
            case 'paid':
                this.command = 'REVIEW_PAID';
                this.action = '846';
                this.id = 'review';
                break;
        }

        this.init();

        this.setDefaultSize(mode);

        $BaseDialog.open(this.id);
    },

    handle: function(x) {
        if (!is_null(x)) {
            var props = x['props'];
            var total = parseInt(x['total'] || 0);
            var status = x['status'];
            var path = x['path'];

            $updateSublineData(default_action, x, props, total, status, path);
        }

        $BaseDialog.close();

        this.term();
    },

    validate: function() {
        this.params = {
            'command':this.command, 
            'review_duedate' : $("#review_duedate").val(), 
            'with_mail' : $("#item-with-mail").prop('checked') ? 1 : 0
        };

        should_be_updated = true;
        selected_menu_action = this.action;
        $InProgress(this.ob, 1);
        $Handle(this.action, function(x) { $ProvisionReviewDialog.handle(x); }, this.params);
    },

    set_unread: function(ob) {
        this.ob = ob;
        this.action = '848';
        this.command = 'SET_UNREAD';

        this.params = {
            'command':this.command
        };

        should_be_updated = true;
        selected_menu_action = this.action;
        $InProgress(this.ob, 1);
        $Handle(this.action, function(x) { $ProvisionReviewDialog.done(x); }, this.params);
    },

    set_read: function(ob, mode) {
        this.ob = ob;
        this.action = '849';
        this.command = 'SET_READ';
        this.mode = mode;

        this.params = {
            'command':this.command,
            'mode':mode || ''
        };

        should_be_updated = true;
        selected_menu_action = this.action;
        $InProgress(this.ob, 1);
        $Handle(this.action, function(x) { $ProvisionReviewDialog.done(x); }, this.params);
    },

    print_order: function(ob) {
        this.ob = ob;
        this.action = default_print_action;
        this.command = 'PRINT_ORDER';

        this.params = {
            'command':this.command
        };

        should_be_updated = true;
        selected_menu_action = this.action;
        $InProgress(this.ob, 1);
        $Handle(this.action, function(x) { $ProvisionReviewDialog.done(x); }, this.params);
    },

    done: function(x) {
        var self = $ProvisionReviewDialog;

        $InProgress(self.ob, 0);

        //alert('printOrder:'+(should_be_updated ? 1 : 0));

        if (should_be_updated) {
            var ob = SelectedGetItem(LINE, 'ob');
            var items = self.mode == 'all' ? $LineSelector.getSelectedItems(null) : [ob];

            switch (self.command) {
                case 'SET_UNREAD':
                    ob.addClass("unread");
                    break;
                case 'SET_READ':
                    items.forEach(function(x, index) {
                        x.removeClass("unread");
                    });
                    break;
                case 'PRINT_ORDER':
                    printProvisionOrder(x);
                    break;
            }
        }

        self.term();
    },

    cancel: function() {
        $BaseDialog.cancel();

        this.term();
    }
};

var $ProvisionOrderHistoryDialog = {
    base         : $BaseScreenDialog,

    // =============================
    // Provision Order History Class
    // =============================

    IsDebug : 0, IsTrace : 0, IsLog : 0,

    action       : '',
    command      : null,
    id           : null,
    params       : null,

    // Mode of screen available
    mode         : 'client',
    // Flag to lock screen
    with_lock    : 1,

    init: function(ob) {
        this.base.init(ob, this.id, this);
    },

    term: function() {
        this.base.term();

        this.action = '';
        this.command = null;
        this.id = null;
        this.params = null;
        
        selected_menu_action = '';
    },

    reset: function() {
        this.base.reset(true);

        var tab = $("#"+this.id+"-view-content");

        if (!is_exist(tab))
            return;

        $TablineSelector.init(tab);
    },

    lock_scroll: function() {
        if (!this.with_lock)
            return;

        this.base.lock_scroll();
    },

    unlock_scroll: function() {
        if (!this.with_lock)
            return;

        this.base.unlock_scroll();
    },

    setDefaultSize: function() {
        var offset = {'H' : [190, 5, 0], 'W' : [64, 0, 0], 'init' : [0, -120]}; // +16

        this.base.setDefaultSize(offset);

        $BaseDialog.open(this.id);
    },

    open: function(ob, mode) {
        if (this.IsTrace)
            alert('$ProvisionOrderHistoryDialog.open, mode:'+mode);

        switch (mode) {
            case 'order':
                this.command = 'ORDER_HISTORY';
                this.action = '853';
                this.id = 'history';
                break;
        }

        this.init(ob);

        this.validate();
    },

    handle: function(x) {
        var self = $ProvisionOrderHistoryDialog;

        if (!is_null(x)) {
            var data = x['data'];
            var props = x['props'];

            this.base.load(
                $updateTabData(selected_menu_action, data['data'], data['config'], data['total'], data['status'], null)
                    .replace('tab-view-content', this.base.cacheid)
            );
        }

        this.base.handle(function() { $ProvisionOrderHistoryDialog.setDefaultSize(); });
    },

    validate: function() {
        this.params = {
            'command':this.command, 
            'history_duedate' : $("#history_duedate").val()
        };

        should_be_updated = true;
        selected_menu_action = this.action;

        this.base.progress();

        $Handle(this.action, function(x) { $ProvisionOrderHistoryDialog.handle(x); }, this.params);
    },

    onClose: function() {
        this.term();
    },

    confirmed: function() {
        $BaseDialog.close();
    },

    cancel: function() {
        $BaseDialog.cancel();
    }
};

// =======
// Dialogs
// =======

jQuery(function($) 
{
    // --------------------------------
    // Create Scenario Generator Dialog
    // --------------------------------

    $("#provisionuploader-confirm-container").dialog({
        autoOpen: false,
        width:590,
        height:270,
        position:0,
        buttons: [
            {text: keywords['Run'],    click: function() { $BaseDialog.confirmed(); }},
            {text: keywords['Reject'], click: function() { $BaseDialog.cancel(); }}
        ],
        modal: false,
        draggable: true,
        resizable: true,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $BaseDialog.onClose();
        }
    });

    // -----------------------------
    // Create Provision Order Dialog
    // -----------------------------

    $("#order-confirm-container").dialog({
        autoOpen: false,
        width:0,
        height:0,
        position:0,
        buttons: [
            {text: keywords['Save'],   click: function() { $ProvisionSelectorDialog.validate(); }},
            {text: keywords['Cancel'], click: function() { $ProvisionSelectorDialog.cancel(); }}
        ],
        modal: true,
        draggable: true,
        resizable: true,
        //position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $ProvisionSelectorDialog.onClose();
            $BaseDialog.onClose();
        },
        open: function() {
            var mode = $ProvisionSelectorDialog.mode;
            var width = $(this).parent().outerWidth();
            var height = $(this).parent().outerHeight();
            var left = int(($_width(mode) - width) / 2);
            var top = int(($_height(mode) - height) / 2);

            $(this).parent().css({position: 'fixed', left: left, top: top});
        }
    });

    // --------------------------
    // Confirmation Review Dialog
    // --------------------------

    $("#review-confirm-container").dialog({
        autoOpen: false,
        width:520,
        height:300,
        position:0,
        buttons: [
            {text: keywords['Run'],    click: function() { $ProvisionReviewDialog.validate(); }},
            {text: keywords['Reject'], click: function() { $ProvisionReviewDialog.cancel(); }}
        ],
        modal: false,
        draggable: true,
        resizable: false,
        position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $BaseDialog.onClose();
        }
    });

    // ----------------------------
    // Order Changes History Dialog
    // ----------------------------

    $("#history-confirm-container").dialog({
        autoOpen: false,
        width:0,
        height:0,
        position:0,
        buttons: [
            {text: keywords['OK'],     click: function() { $ProvisionOrderHistoryDialog.confirmed(); }},
            {text: keywords['Cancel'], click: function() { $ProvisionOrderHistoryDialog.cancel(); }}
        ],
        modal: true,
        draggable: true,
        resizable: false,
        //position: {my: "center center", at: "center center", of: window, collision: "none"},
        create: function (event, ui) {
            $(event.target).parent().css("position", "fixed");
        },
        close: function() {
            $ProvisionOrderHistoryDialog.onClose();
            $BaseDialog.onClose();
        },
        open: function() {
            var mode = $ProvisionOrderHistoryDialog.mode;
            var width = $(this).parent().outerWidth();
            var height = $(this).parent().outerHeight();
            var left = int(($_width(mode) - width) / 2);
            var top = int(($_height(mode) - height) / 2);

            $(this).parent().css({
                position: 'fixed',
                left: left,
                top: top
            });
        }
    });
});
