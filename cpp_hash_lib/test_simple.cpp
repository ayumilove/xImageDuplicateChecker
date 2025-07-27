#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    vector<char> buffer;
    string size_str = "test";
    buffer.insert(buffer.end(), size_str.begin(), size_str.end());
    
    for (char c : buffer) {
        cout << c;
    }
    cout << endl;
    
    return 0;
}