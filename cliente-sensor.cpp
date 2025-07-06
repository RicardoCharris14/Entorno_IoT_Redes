#include <iostream>
#include <ctime>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

int PORT = 8080;
std::string ADDR = "127.0.0.1";

// Convierte uint64_t a big-endian
uint64_t htonll(uint64_t value) {
    if (__BYTE_ORDER == __LITTLE_ENDIAN) {
        return (((uint64_t)htonl(value & 0xFFFFFFFF)) << 32) | htonl(value >> 32);
    } else {
        return value;
    }
}

// Convierte float a uint32_t big-endian
uint32_t float_to_network(float value) {
    uint32_t as_int;
    static_assert(sizeof(float) == sizeof(uint32_t), "float y uint32_t deben tener el mismo tamaño");
    std::memcpy(&as_int, &value, sizeof(float));
    return htonl(as_int);
}

int main(){
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server{};
    server.sin_family = AF_INET;
    server.sin_port = htons(PORT);
    inet_pton(AF_INET, ADDR.c_str(), &server.sin_addr);

    connect(sock, (sockaddr*)&server, sizeof(server));

    int16_t id = htons(2);
    uint64_t fecha_hora = htonll(time(nullptr));
    uint32_t temperatura = float_to_network(23.5f);
    uint32_t presion = float_to_network(1.02f);
    uint32_t humedad = float_to_network(50.0f);

    char buffer[22];
    memcpy(buffer, &id, 2);
    memcpy(buffer + 2, &fecha_hora, 8);
    memcpy(buffer + 10, &temperatura, 4);
    memcpy(buffer + 14, &presion, 4);
    memcpy(buffer + 18, &humedad, 4);

    send(sock, buffer, sizeof(buffer), 0);

    close(sock);
    return 0;
}