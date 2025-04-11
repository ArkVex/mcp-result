class Solution {
    public:
        string addBinary(string a, string b) {
            int length;
            int arr[length+1];
            if(a.len()>=b.len()){
                length=a.len();
            }
            else
            length=b.len();
            int carry=0;
            int arr[length+1];
            for(int i=length-1;i>=0;i--){
                if(a[i]=='1' && b[i]=='1'){
                    arr[i]=carry;
                    carry=1;
                }
                else if(a[i]=='0' && b[i]=='0'){
                    arr[i]=carry;
                    carry=0;
                }
                else{
                    if(carry==1){
                        arr[i]=0;
                        carry=1;
                    }
                    else{
                        arr[i]=1;
                        carry=0;
                    }
                }
            }
            if(carry==1){
                arr[length]=1;
                length++;
            }
            return arr;
        }
    };