# This program scrapes Kireicake (a manga translation site) for new chapter updates
# series{
#   title{
#       series title's text and hyperlink to series page
#   }
#   element{
#       title div{
#           Chapter text and Chapter's Hyperlink
#       }
#       meta_r{
#           Translator's Info, Release Date
#       }
#   }
# }
import KireiCakeModule

#find_new_chapters(titles)
KireiCakeModule.latest_release()

# -w KC [Dai Dark] # the search parameter command to call the KireiCake search function
