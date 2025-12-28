#include <stdio.h>
#include <time.h>
#include <stdbool.h>

#define MAX_TOKEN_LEN 256

bool is_word_char(unsigned char c) {
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-') return true;
    if (c == 0xD0 || c == 0xD1) return true; 
    return false;
}

void to_lower_utf8(unsigned char* buf, int len) {
    for (int i = 0; i < len; ++i) {
        if (buf[i] >= 'A' && buf[i] <= 'Z') {
            buf[i] += 32;
        } else if (buf[i] == 0xD0 && i + 1 < len) {
            if (buf[i+1] >= 0x90 && buf[i+1] <= 0x9F) buf[i+1] += 0x20;
            else if (buf[i+1] >= 0xA0 && buf[i+1] <= 0xAF) { buf[i] = 0xD1; buf[i+1] -= 0x20; }
            else if (buf[i+1] == 0x81) { buf[i] = 0xD1; buf[i+1] = 0x91; }
        }
    }
}

int main() {
    unsigned char buf[MAX_TOKEN_LEN];
    int len = 0;
    long long total_tokens = 0, total_len = 0, total_bytes = 0;
    clock_t start = clock();
    int c;

    while ((c = getchar()) != EOF) {
        total_bytes++;
        unsigned char uc = (unsigned char)c;
        if (is_word_char(uc)) {
            if (len < MAX_TOKEN_LEN - 2) {
                buf[len++] = uc;
                if (uc == 0xD0 || uc == 0xD1) {
                    int c2 = getchar();
                    if (c2 != EOF) { total_bytes++; buf[len++] = (unsigned char)c2; }
                }
            }
        } else {
            if (len > 0) {
                buf[len] = '\0'; to_lower_utf8(buf, len);
                printf("%s\n", buf);
                total_tokens++; total_len += len; len = 0;
            }
        }
    }
    clock_t end = clock();
    double sec = (double)(end - start) / CLOCKS_PER_SEC;
    fprintf(stderr, "\n--- СТАТИСТИКА ---\n");
    fprintf(stderr, "Токенов: %lld\n", total_tokens);
    fprintf(stderr, "Время: %.4f сек\n", sec);
    fprintf(stderr, "Скорость: %.2f КБ/с\n", sec > 0 ? (total_bytes/1024.0)/sec : 0);
    return 0;
}
