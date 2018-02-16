// *************************************
// BANKPERSO PAGE DECLARATION: /log.html
// -------------------------------------
// Version: 1.0
// Date: 13-06-2015

LINE = 'order';
SUBLINE = 'batch';

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
    SelectedReset();

    var parent = $("#log-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(LINE, ob, 'add');

    var parent = $("#batches-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(SUBLINE, ob, 'add');

    $ShowMenu(null);

    interrupt(true, 1, 0, null, 0);
}

function $Go(action) {
    $web_logging(action);
}

function $ShowOnStartup() {
    $Go('301');
}

function $ShowMenu(id) {
    //
    // Show (open) selected right side's Data menu item (Parameters/Products)
    //
    var batches = $("#batches-content");
    var statuses = $("#statuses-content");

    if (!id)
        id = 'data-menu-batches';

    if (selected_data_menu)
        selected_data_menu.removeClass('selected');

    selected_data_menu = $("#"+id);
    //$("#data-content").scrollTop(0);

    if (id == 'data-menu-batches') {
        statuses.hide();
        batches.show();
    } else {
        batches.hide();
        statuses.show();
    }

    selected_data_menu.addClass('selected');
    selected_data_menu_id = id;
}

function $HideLogPage() {
    if (current_subline) {
        var selected_item = SelectedGetItem(SUBLINE, 'ob');
        if (selected_item != null)
            $onToggleSelectedClass(SUBLINE, selected_item, 'remove');
    }
}

function $ShowLogPage() {
    if (current_subline) {
        $onToggleSelectedClass(SUBLINE, current_subline, 'add');
    }
}

function $ResetLogPage() {
    current_subline = null;
}

function $onParentFormSubmit(id) {
    var frm = $("#"+id);
    var action = frm.attr('action');

    //alert(frm.attr('id'));

    frm.submit();
}

function $onToggleSelectedClass(key, ob, action) {
    var id = ob.attr("id");

    //alert(ob.attr('id')+':'+action);

    if (action == 'submit') {
        $("input[name^='file_id']").each(function() { $(this).val(id); });
        $onParentFormSubmit('filter-form');
    } else {
        $("td", ob).each(function() {
            if (action == 'add') {
                $(this).addClass("selected");
                if (key == LINE)
                    $("input[name^='file_id']").each(function() { $(this).val(id); });
                SelectedSetItem(key, 'ob', ob);
            }
            else
                $(this).removeClass("selected");
        });
    }
}

// ===========================
// Dialog windows declarations
// ===========================

// ====================
// Page Event Listeners
// ====================

jQuery(function($) 
{
    // ----------------------
    // Select log row (click)
    // ----------------------
    function $onLogClick(ob) {
        if (isWebServiceExecute)
            return;

        SelectedSetItem(LINE, 'id', null);

        $GetLogItem(ob);
    } 

    $("#log-content").on('click', '.log-row', function(e) {
        SelectedSetItem(LINE, 'num', 0);

        $onLogClick($(this));

        e.preventDefault();
    });

    // ----------------------------
    // Select log page (Pagination)
    // ----------------------------
    function $onSubmitPage() {
        if (isWebServiceExecute)
            return;

        $_reset_page();

        if (current_page) {
            IsGoPagination = true;

            $Go();
        }
    }

    function $onSortClick(ob) {
        $_next_current_sort();

        var x = LOG_SORT[current_sort];
        ob.attr('title', page_sort_title+(x ? ' ['+x+']' : ''));

        $onSubmitPage();
    }

    /*
    function $onPaginationClick(ob) {
        var id = ob.attr('id');
        if (id == 'page:prev' && current_page > 0)
            current_page -= 1;
        else if (id == 'page:next')
            current_page += 1;
        else
            current_page = int(id.split(':')[1]);

        $onSubmitPage();
    }

    function $onPerPageChanged(ob) {
        var value = ob.val();

        per_page = int(value);
        current_page = 1;

        $onSubmitPage();
    }

    function $onOrderTypeFilterChanged(ob) {
        var value = ob.val();

        current_order_type = (value == 'x' ? -1: value);
        current_page = 1;

        $onSubmitPage();
    }
    */

    $("#sort_icon").click(function(e) {
        $onSortClick($(this));
        e.preventDefault();
    });

    /*
    $("#log-pagination").on('click', '.enabled', function(e) {
        $onPaginationClick($(this));
        e.preventDefault();
    });

    $("#log-pagination").on('change', '#per-page', function(e) {
        $onPerPageChanged($(this));
        e.preventDefault();
    });

    $("#log-pagination").on('change', '#filter-otype', function(e) {
        $onOrderTypeFilterChanged($(this));
        e.preventDefault();
    });

    $("#filter-otype").change(function(e) {
        $onOrderTypeFilterChanged($(this));
        e.preventDefault();
    });
    */

    $(".line").click(function(e) {
        var ob = $(this);
        $onToggleSelectedClass(LINE, ob, 'submit');
    });

    $(".subline").click(function(e) {
        current_subline = $(this);

        $HideLogPage();
        SelectedSetItem(SUBLINE, 'ob', current_subline);

        $Go('301');
    });

    // --------------------
    // Right side Data menu
    // --------------------

    $("div[id^='data-menu']", this).click(function(e) {
        var ob = $(this);
        var id = ob.attr('id');

        $ShowMenu(id);
    });

    // -------------
    // Command Panel
    // -------------

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
        //var s = $("#search-context").val();
        //alert('search:'+s);
        if (s.length>0) {
            search_context = s;
            $("input[id^='searched']").each(function() { $(this).val(s); });
            is_search_activated = true;

            $_reset_current_sort();
            $onSubmitPage();
        }
        //if (e != null) e.preventDefault();
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
        alert('Document Ready (index)');

    $("#search-context").attr('placeholder', 'Найти (имя файла, ТЗ)...');

    $_init();
});
