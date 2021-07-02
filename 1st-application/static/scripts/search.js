$(document).ready(function(){
    $("#livebox").on("input",function(e){
        $("#datalist").empty();
        $.ajax({
            method: "post",
            url: "/search",
            data: {text: $("#livebox").val()},
            success: function(res) {
                var data = "<ul>";
                $.each(res,function(index,value){
                    console.log(value.username);
                    data += "<li>" + value.username;
                    data += "<p id='" + value.username + "' class='select-room'>Send Message</p>";
                    data += "</li>";
                });
                data += "</ul>";
                $("#datalist").html(data);
            }
        });
    });
});