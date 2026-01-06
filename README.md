# customer-cli
Start menu for your terminal.


#------------------------------------------------------------------
# To run
#------------------------------------------------------------------

python /path/to/menufolder/startmenu.py

#------------------------------------------------------------------
# To use as a startmenu in zsh add this line
#------------------------------------------------------------------

if [ -z "$GHOSTTY_MENU_SHOWN" ]; then
    export GHOSTTY_MENU_SHOWN=1
    ~/.config/customenu-cli/startmenu.py
fi

#------------------------------------------------------------------
