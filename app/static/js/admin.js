// *************************************
// BANKPERSO PAGE DECLARATION: /log.html
// -------------------------------------
// Version: 1.10
// Date: 28-07-2017

default_submit_mode = 2;
default_action      = '100';
default_log_action  = '101';
default_input_name  = 'user_id';

LINE    = 'admin';
SUBLINE = '';

// ----------------------
// Dialog Action Handlers
// ----------------------

function $_reset_current_sort() {
    current_page = 1;
}

function $_next_current_sort() {
    current_sort = current_sort == LOG_SORT.length-1 ? 0 : current_sort + 1;
    $_reset_current_sort();
}

function $_deactivate_search() {
    is_search_activated = false;
    search_context = '';
    current_page = 1;
}

function $_reset_item() {
    refresh_current_state = true;
    SelectedReset();
}

function $_reset_page() {
    SelectedReset();
    current_row_id = null;
}

function $_calculating_disabled() {
    return false;
}

// --------------
// Page Functions
// --------------

function $Init() {
    $SidebarControl.init();

    $_reset_current_sort();

    SelectedReset();

    $LineSelector.init();

    var parent = $("#admin-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(LINE, ob, 'add');

    $LineSelector.set_current(ob);
    $ResetPageState();

    $ShowMenu(null);

    // ------------------------
    // Start default log action
    // ------------------------

    interrupt(true, 1);
}

function $ResetPageState() {
    $ProfileClients.init();
    $ProfileClients.update($("#profile_clients").val());
}

function $ShowMenu(id) {
    selected_data_menu_id = null;
}

function $onUserFormSubmit() {
    var ob = $("#item-clients-all");
    $("#profile_clients").val(!ob.prop('checked') ? $ProfileClients.getItems().join(DEFAULT_HTML_SPLITTER) : '');
    return true;
}

function $onPaginationFormSubmit() {
    return true;
}

function $onFilterFormSubmit(frm) {
    return true;
}

// ===========================
// Dialog windows declarations
// ===========================

function MakeFilterSubmit(mode, page) {
    $("#filter-form").attr("action", baseURI);

    switch (mode) {

        // -------------
        // Submit modes:
        // -------------

        case 0:
            break;

        // ---------------------------
        // LineSelector Handler submit
        // ---------------------------

        case 9:
            $("#user_id").each(function() { $(this).val(0); });
    }

    $ResetLogPage();
    $setPaginationFormSubmit(page);
    $onParentFormSubmit('filter-form');
}

// ====================
// Page Event Listeners
// ====================

jQuery(function($) 
{
    // --------------
    // Line selection
    // --------------

    $(".line").click(function(e) {
        var ob = $(this);
        $LineSelector.set_current(ob);
        $onToggleSelectedClass(LINE, ob, 'submit', null);

        isKeyboardDisabled = true;
    });

    // -----------
    // User's Form
    // -----------

    $("#user-form").on('change', $("input, select"), function(e) {
        $setUserFormSubmit(0);
    });

    // -----------------------
    // User's Profile. Clients
    // -----------------------

    $("input[id^='item-clients-all']").on('change', function(e) {
        var checked = $(this).prop('checked') ? true : false;
        $ProfileClients.activate(checked);
    });

    $("li[name^='cid:']").on('click', $("#profile-clients-left"), function(e) {
        var ob = $(this);
        var parent = ob.parents("*[class^='profile-data-panel']").first();
        var disabled = parent.hasClass('disabled');

        if (disabled) return;
        
        //alert(ob.attr('id')+':'+parent.attr('id')+':'+disabled);

        $ProfileClients.setLeft(ob, false);
    });

    $("li[name^='cid:']").on('click', $("#profile-clients-right"), function(e) {
        var ob = $(this);
        var parent = ob.parents("*[class^='profile-data-panel']").first();
        var disabled = parent.hasClass('disabled');

        if (disabled) return;
        
        //alert(ob.attr('id')+':'+parent.attr('id')+':'+disabled);

        $ProfileClients.setRight(ob, false);
    });

    $("#profile-clients-include").click(function(e) {
        var ob = $(this);
        var disabled = ob.hasClass('disabled');

        if (disabled) return;
        
        //alert(ob.prop('tagName'));

        $ProfileClients.onAddClientProfileItem(ob);
    });

    $("#profile-clients-exclude").click(function(e) {
        var ob = $(this);
        var disabled = ob.hasClass('disabled');

        if (disabled) return;
        
        //alert(ob.prop('tagName'));

        $ProfileClients.onRemoveClientProfileItem(ob);
    });

    // --------------------
    // Right side Data menu
    // --------------------

    $("#add").click(function(e) {
        $("input[name^='command']").val('add');
        var selected_item = SelectedGetItem(LINE, 'ob');
        if (selected_item != null)
            $onToggleSelectedClass(LINE, selected_item, 'remove');

        $onToggleSelectedClass(LINE, $(this), 'clean');
        $cleanUserForm();

        $ProfileClients.reset();
        $ProfileClients.activate(true);

        isKeyboardDisabled = true;
    });

    $("#delete").click(function(e) {
        $("input[name^='command']").val('delete');
        $onParentFormSubmit('command-form');
        //e.preventDefault();
    });

    // -----------------
    // Top Command Panel
    // -----------------

    $("#refresh").click(function(e) {
        $("#command").val('refresh');
        $onParentFormSubmit('filter-form');
        e.preventDefault();
    });

    $("#init-filter").click(function(e) {
        $("#command").val('init-filter');
        $onParentFormSubmit('init-form');
        e.preventDefault();
    });

    $("#export").click(function(e) {
        $("#command").val('export');
        $onParentFormSubmit('filter-form');
        e.preventDefault();
    });

    // ---------------------
    // Search context events
    // ---------------------

    function $onSearchSubmit(e) {
        var s = strip($("#search-context").val());
        if (s.length > 0) {
            search_context = s;
            $("input[id^='searched']").each(function() { $(this).val(s); });
            is_search_activated = true;

            $_reset_current_sort();
            $onSubmitPage();
        }
    }

    $("#search-context").focusin(function(e) {
        is_search_focused = true;
    }).focusout(function(e) {
        is_search_focused = false;
    });

    $("#search-icon").click(function(e) {
        $onSearchSubmit(null);
        $onParentFormSubmit('filter-form');
    });

    $("#search-form").submit(function(e) {
        $onSearchSubmit(e);
    });

    // -------------
    // Resize window
    // -------------

    // --------
    // Keyboard
    // --------
});

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (admin)');

    current_context = 'admin';

    $("#search-context").attr('placeholder', 'Найти (name, login, email)...');

    document.oncontextmenu = function() { return false; };

    $_init();
});
