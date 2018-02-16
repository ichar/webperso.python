// *********************************************
// ORDERSTATE PAGE DECLARATION: /orderstate.html
// ---------------------------------------------
// Version: 1.40
// Date: 05-09-2017

default_submit_mode = 2;
default_action      = '500';
default_log_action  = '501';
default_input_name  = 'order_id';

LINE    = 'order';
SUBLINE = 'event';

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

    page_sort_title = $("#sort_icon").attr('title');

    SelectedReset();

    $LineSelector.init();

    var parent = $("#line-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(LINE, ob, 'add', null);

    $LineSelector.set_current(ob);

    $SublineSelector.init();

    var parent = $("#subline-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(SUBLINE, ob, 'add', null);

    $SublineSelector.set_current(ob);

    $ShowMenu('data-menu-events');

    $TabSelector.init();

    // ------------------------
    // Start default log action
    // ------------------------

    interrupt(true, 1);
}

function $ActivateInfoData(show) {
    var container = $("#info-data");

    if (show)
        container.show();
    else
        container.hide();
}

function $ShowMenu(id) {
    //
    // Show (open) selected DataMenu item (Tabs)
    //
    var events = $("#subline-content");
    var files = $("#files-content");
    var errors = $("#errors-content");
    var certificates = $("#certificates-content");
    var aliases = $("#aliases-content");
    var log = $("#log-content");

    if (selected_data_menu)
        selected_data_menu.removeClass('selected');

    selected_data_menu = $("#"+id);
    //$("#data-content").scrollTop(0);

    events.hide();
    files.hide();
    errors.hide();
    certificates.hide();
    aliases.hide();
    log.hide();

    if (id == 'data-menu-events')
        events.show();
    else if (id == 'data-menu-files')
        files.show();
    else if (id == 'data-menu-errors')
        errors.show();
    else if (id == 'data-menu-certificates')
        certificates.show();
    else if (id == 'data-menu-aliases')
        aliases.show();
    else if (id == 'data-menu-log')
        log.show();

    if (id == 'data-menu-events' && SelectedGetItem(SUBLINE, 'id'))
        $ActivateInfoData(1);
    else
        $ActivateInfoData(0);

    selected_data_menu.addClass('selected');
    selected_data_menu_id = id;
}

function $onPaginationFormSubmit(frm) {
    return true;
}

function $onFilterFormSubmit(frm) {
    return true;
}

function $onTabSelect(ob) {
    var id = ob.attr('id');
    var action = 
        id == 'data-menu-files' ? '502' : (
        id == 'data-menu-errors' ? '503' : (
        id == 'data-menu-certificates' ? '504' : (
        id == 'data-menu-aliases' ? '505' : (
        id == 'data-menu-log' ? '506' : null
        ))));

    selected_menu_action = action;

    if (action != null) {
        $InProgress(ob, 1);
        $Go(action);
    }
    else if (default_submit_mode > 1) {
        selected_menu_action = default_log_action;
        $InProgress(ob, 1);
        $Go(default_action);
    }
    else
        $ShowMenu(id);

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
        //  0 - changed client
        //  1 - changed exchange type
        //  2 - changed config
        //  3 - changed action
        //  4 - changed date from
        //  5 - changed date to
        //  6 - changed state

        case 0:
            $("#event_id").each(function() { $(this).val(0); });
            $("#type").val(0);
        case 1:
            //$("#status").val(0);
            //$("#batchtype").val(0);
        case 2:
        case 3:
        case 4:
        case 5:
            break;

        // ---------------------------
        // LineSelector Handler submit
        // ---------------------------

        case 9:
            $("#order_id").each(function() { $(this).val(0); });
            $("#event_id").each(function() { $(this).val(0); });
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
    });

    // -----------------
    // SubLine selection
    // -----------------

    $("#subline-content").on('click', '.subline', function(e) {
        var ob = $(this);
        $SublineSelector.onRefresh(ob);
    });

    // ---------------------
    // Data Section progress
    // ---------------------

    $("#data-section").on('click', '.column', function(e) {
        var ob = $(this);
        var parent = ob.parents("*[class*='line']").first();
        if (!is_null(parent) && !parent.hasClass("tabline"))
            $InProgress(ob, 1);
    });

    // ------------------------------
    // Tab table lines data selection
    // ------------------------------

    $(".view-lines").on('click', '.tabline', function(e) {
        var ob = $(this);

        if (!is_null(current_tabline))
            $onToggleSelectedClass(TABLINE, current_tabline, 'remove', null);
        
        current_tabline = ob;
        SelectedSetItem(TABLINE, 'ob', current_tabline);

        $onToggleSelectedClass(TABLINE, current_tabline, 'add', null);
    });

    // --------------
    // Tabs Data menu
    // --------------

    $("div[id^='data-menu']", this).click(function(e) {
        $TabSelector.onClick($(this));
    });

    // -------------
    // Resize window
    // -------------

    // --------
    // Keyboard
    // --------
    /*
    $(window).keydown(function(e) {
        var exit = false;

        if (e.ctrlKey || e.shiftKey) {
            if (isWebServiceExecute)
                return;
            if (e.keyCode==38)                          // Ctrl-Up
                exit = $LineSelector.up();
            else if (e.keyCode==40)                     // Ctrl-Down
                exit = $LineSelector.down();
            else if (e.ctrlKey && e.keyCode==36)        // Ctrl-Home
                exit = $LineSelector.home();
            else if (e.shiftKey && e.keyCode==33)       // Shift-PgUp
                exit = $LineSelector.pgup();
            else if (e.shiftKey && e.keyCode==34)       // Shift-PgDown
                exit = $LineSelector.pgdown();
            else if (e.ctrlKey && e.keyCode==35)        // Ctrl-End
                exit = $LineSelector.end();
            else if (e.keyCode==9)                      // Ctrl-Tab
                exit = $TabSelector.tab();
            else if (e.ctrlKey && e.keyCode==37)        // Ctrl-Left
                exit = $TabSelector.left();
            else if (e.ctrlKey && e.keyCode==39)        // Ctrl-Right
                exit = $TabSelector.right();
        }

        else if (e.altKey) {
            if (isWebServiceExecute)
                return;
            if (e.keyCode==38)                          // Alt-Up
                exit = $SublineSelector.up();
            else if (e.keyCode==40)                     // Alt-Down
                exit = $SublineSelector.down();
            else if ([33, 36].indexOf(e.keyCode) > -1)  // Alt-Home:Alt-PgUp
                exit = $SublineSelector.home();
            else if ([34, 35].indexOf(e.keyCode) > -1)  // Alt-End:Alt-PgDown
                exit = $SublineSelector.end();
        }

        if (exit) {
            e.preventDefault();
            return false;
        }
    });
    */
});

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (orderstate)');

    $("#search-context").attr('placeholder', 'Найти (имя пакета, файл)...');

    $_init();
});


