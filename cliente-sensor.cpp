#include <iostream>
#include <fstream>
#include <ctime>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <thread>
#include <chrono>
#include <random>

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/sha.h>
#include <openssl/evp.h>

#define PORT 8080
#define SERVER_ADDR "127.0.0.1"

// Convierte uint64_t a big-endian
uint64_t htonll(uint64_t value) {
    return ((uint64_t)htonl(value & 0xFFFFFFFF) << 32) | htonl(value >> 32);
}

// Convierte float a uint32_t big-endian
uint32_t float_to_network(float value) {
    uint32_t as_int;
    memcpy(&as_int, &value, sizeof(float));
    return htonl(as_int);
}

// Firma los datos (SHA-256 + RSA) con API moderna
unsigned char* firmar_sha256(const char* mensaje, size_t len, size_t& firma_len) {
    FILE* fp = fopen("private_key.pem", "r");
    if (!fp) throw std::runtime_error("No se pudo abrir private_key.pem");
    
    EVP_PKEY* pkey = PEM_read_PrivateKey(fp, nullptr, nullptr, nullptr);
    fclose(fp);
    if (!pkey) throw std::runtime_error("Error leyendo la clave privada");

    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    if (!mdctx) {
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error creando el contexto de firma");
    }

    if (EVP_DigestSignInit(mdctx, nullptr, EVP_sha256(), nullptr, pkey) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error inicializando DigestSign");
    }

    if (EVP_DigestSignUpdate(mdctx, mensaje, len) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error actualizando DigestSign");
    }

    // Obtiene el tamaño necesario
    if (EVP_DigestSignFinal(mdctx, nullptr, &firma_len) != 1) {
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error obteniendo tamaño de firma");
    }

    unsigned char* firma = new unsigned char[firma_len];
    if (EVP_DigestSignFinal(mdctx, firma, &firma_len) != 1) {
        delete[] firma;
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);
        throw std::runtime_error("Error generando la firma");
    }

    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return firma;
}

// Funciones de sensores
std::random_device rd;
std::mt19937 gen(rd());

float generar_temperatura() {
    std::uniform_real_distribution<float> dis(0.0f, 30.0f);
    return std::round(dis(gen) * 10.0f) / 10.0f;
}
float generar_presion() {
    std::uniform_real_distribution<float> dis(0.7f, 1.3f);
    return std::round(dis(gen) * 100.0f) / 100.0f;
}
float generar_humedad() {
    std::uniform_real_distribution<float> dis(0.0f, 100.0f);
    return std::round(dis(gen) * 10.0f) / 10.0f;
}

int main() {
    SSL_library_init();
    OpenSSL_add_all_algorithms();
    SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
    if (!ctx) {
        std::cerr << "Error creando contexto SSL." << std::endl;
        return 1;
    }

    while (true) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in server{};
        server.sin_family = AF_INET;
        server.sin_port = htons(PORT);
        inet_pton(AF_INET, SERVER_ADDR, &server.sin_addr);

        if (connect(sock, (sockaddr*)&server, sizeof(server)) < 0) {
            std::cerr << "Error al conectar con el servidor." << std::endl;
            close(sock);
            std::this_thread::sleep_for(std::chrono::seconds(5));
            continue;
        }

        SSL* ssl = SSL_new(ctx);
        SSL_set_fd(ssl, sock);
        if (SSL_connect(ssl) <= 0) {
            std::cerr << "Error en el handshake TLS." << std::endl;
            SSL_free(ssl);
            close(sock);
            std::this_thread::sleep_for(std::chrono::seconds(5));
            continue;
        }

        std::ifstream f("id.txt");
        int id_val = 1;
        if (f >> id_val) f.close();

        int16_t id = htons(id_val);
        uint64_t ts = htonll(time(nullptr));
        uint32_t temp = float_to_network(generar_temperatura());
        uint32_t pres = float_to_network(generar_presion());
        uint32_t hum = float_to_network(generar_humedad());

        char buffer[22];
        memcpy(buffer, &id, 2);
        memcpy(buffer + 2, &ts, 8);
        memcpy(buffer + 10, &temp, 4);
        memcpy(buffer + 14, &pres, 4);
        memcpy(buffer + 18, &hum, 4);

        size_t firma_len;
        unsigned char* firma = firmar_sha256(buffer, sizeof(buffer), firma_len);

        size_t total_len = sizeof(buffer) + firma_len;
        char* mensaje = new char[total_len];
        memcpy(mensaje, buffer, sizeof(buffer));
        memcpy(mensaje + sizeof(buffer), firma, firma_len);

        SSL_write(ssl, mensaje, total_len);

        std::cout << "Datos con ID " << id_val << " enviados con firma RSA" << std::endl;
        std::ofstream out("id.txt"); out << id_val + 1; out.close();

        delete[] mensaje;
        delete[] firma;

        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(sock);
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    SSL_CTX_free(ctx);
    return 0;
}
