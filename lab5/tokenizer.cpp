#include <stdio.h>
#include <stdbool.h>
#include <string.h>

#define MAX_TOKEN_LEN 256


bool is_word_char(unsigned char c) {
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-') return true;
    if (c == 0xD0 || c == 0xD1) return true; 
    return false;
}

void to_lower_utf8(unsigned char* buf, int len) {
    for (int i = 0; i < len; ++i) {
        if (buf[i] >= 'A' && buf[i] <= 'Z') buf[i] += 32;
        else if (buf[i] == 0xD0 && i + 1 < len) {
            if (buf[i+1] >= 0x90 && buf[i+1] <= 0x9F) buf[i+1] += 0x20;
            else if (buf[i+1] >= 0xA0 && buf[i+1] <= 0xAF) { buf[i] = 0xD1; buf[i+1] -= 0x20; }
            else if (buf[i+1] == 0x81) { buf[i] = 0xD1; buf[i+1] = 0x91; }
        }
    }
}


bool is_vowel(unsigned char* s) {
    if (*s == 0xD0) {
        unsigned char n = *(s+1);
        // а, е, и, о, у, э, ю, я
        return (n==0xB0 || n==0xB5 || n==0xB8 || n==0xBE || n==0x83 || n==0x8D || n==0x8E || n==0x8F);
    } else if (*s == 0xD1) {
        unsigned char n = *(s+1);
        // ы, ё
        return (n==0x8B || n==0x91);
    }
    return false;
}

int get_rv(unsigned char* word, int len) {
    for (int i = 0; i < len - 1; ++i) {
        if (is_vowel(word + i)) {
            return i + 2;
        }
        if (word[i] == 0xD0 || word[i] == 0xD1) i++;
    }
    return len;
}

int match_suffix(unsigned char* word, int len, int rv, const char* suffix) {
    int slen = strlen(suffix);
    if (len - rv < slen) return 0; 
    
    for (int i = 0; i < slen; ++i) {
        if (word[len - slen + i] != (unsigned char)suffix[i]) return 0;
    }
    return slen;
}

void stem_russian(unsigned char* word, int* len) {
    int rv = get_rv(word, *len);
    if (rv >= *len) return; 

    int slen = 0;

    const char* ADJECTIVE[] = {
        "\xD0\xB5\xD0\xB5", "\xD0\xB8\xD0\xB5", "\xD1\x8B\xD0\xB5", "\xD0\xBE\xD0\xB5", 
        "\xD0\xB8\xD0\xBC\xD0\xB8", "\xD1\x8B\xD0\xBC\xD0\xB8", "\xD0\xB5\xD0\xB9", 
        "\xD0\xB8\xD0\xB9", "\xD1\x8B\xD0\xB9", "\xD0\xBE\xD0\xB9", "\xD0\xB5\xD0\xBC", 
        "\xD0\xB8\xD0\xBC", "\xD1\x8B\xD0\xBC", "\xD0\xBE\xD0\xBC", "\xD0\xB5\xD0\xB3\xD0\xBE", 
        "\xD0\xBE\xD0\xB3\xD0\xBE", "\xD0\xB5\xD0\xBC\xD1\x83", "\xD0\xBE\xD0\xBC\xD1\x83", 
        "\xD0\xB8\xD1\x85", "\xD1\x8B\xD1\x85", "\xD1\x83\xD1\x8E", "\xD1\x8E\xD1\x8E", 
        "\xD0\xB0\xD1\x8F", "\xD1\x8F\xD1\x8F", NULL
    };

    bool adj_found = false;
    for (int i = 0; ADJECTIVE[i] != NULL; i++) {
        if ((slen = match_suffix(word, *len, rv, ADJECTIVE[i]))) {
            *len -= slen;
            adj_found = true;
            break;
        }
    }

    if (!adj_found) {
        const char* NOUN[] = {
            "\xD0\xB0", "\xD0\xB5\xD0\xB2", "\xD0\xBE\xD0\xB2", "\xD0\xB8\xD0\xB5", 
            "\xD1\x8C\xD0\xB5", "\xD0\xB5", "\xD0\xB8\xD1\x8F\xD0\xBC\xD0\xB8", 
            "\xD1\x8F\xD0\xBC\xD0\xB8", "\xD0\xB0\xD0\xBC\xD0\xB8", "\xD0\xB5\xD0\xB9", 
            "\xD0\xB8\xD0\xB9", "\xD0\xB8", "\xD0\xB8\xD0\xB5\xD0\xB9", "\xD0\xB5\xD0\xB9", 
            "\xD0\xBE\xD0\xB9", "\xD0\xB8\xD0\xBC\xD0\xB8", "\xD1\x8B\xD0\xBC\xD0\xB8", 
            "\xD0\xBE\xD0\xBC", "\xD0\xB0\xD0\xBC", "\xD1\x8F\xD0\xBC", "\xD0\xB0\xD1\x85", 
            "\xD1\x8F\xD1\x85", "\xD1\x8B", "\xD1\x8C\xD1\x8E", "\xD0\xB8\xD1\x8E", 
            "\xD1\x8C", "\xD1\x8F", "\xD1\x8E", "\xD0\xBE", "\xD1\x83", NULL
        };
        for (int i = 0; NOUN[i] != NULL; i++) {
            if ((slen = match_suffix(word, *len, rv, NOUN[i]))) {
                *len -= slen;
                break;
            }
        }
    }
    
    if ((slen = match_suffix(word, *len, rv, "\xD0\xB8"))) { // "и"
        *len -= slen;
    }
    
    if ((slen = match_suffix(word, *len, rv, "\xD0\xBE\xD1\x81\xD1\x82\xD1\x8C"))) { // "ость"
        *len -= slen;
    }
}


int main() {
    unsigned char buf[MAX_TOKEN_LEN];
    int len = 0;
    
    int c;
    while ((c = getchar()) != EOF) {
        unsigned char uc = (unsigned char)c;
        if (is_word_char(uc)) {
            if (len < MAX_TOKEN_LEN - 2) {
                buf[len++] = uc;
                if (uc == 0xD0 || uc == 0xD1) {
                    int c2 = getchar();
                    if (c2 != EOF) buf[len++] = (unsigned char)c2;
                }
            }
        } else {
            if (len > 0) {
                buf[len] = '\0';
                
                to_lower_utf8(buf, len);
                
                stem_russian(buf, &len);
                buf[len] = '\0';

                printf("%s\n", buf);
                len = 0;
            }
        }
    }
    if (len > 0) {
        buf[len] = '\0';
        to_lower_utf8(buf, len);
        stem_russian(buf, &len);
        buf[len] = '\0';
        printf("%s\n", buf);
    }
    return 0;
}
